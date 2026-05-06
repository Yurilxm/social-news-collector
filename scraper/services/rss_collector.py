import logging
import os
import re
import time
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import feedparser
import requests
from requests import HTTPError
from bs4 import BeautifulSoup

from .tinydb_service import TinyDBService

# Caminho do banco
DB_PATH = os.path.join(os.getcwd(), "db")


class RSSSourceConfig:
    """Classe simples para config de fonte RSS (substitui bot.config_loader)"""
    def __init__(self, name: str, url: str, is_active: bool = True):
        self.name = name
        self.url = url
        self.is_active = is_active


class RSSCollector:
    def __init__(self) -> None:
        self.logger = logging.getLogger("rss_collector")
        self.tinydb = TinyDBService()
        self.http = requests.Session()
        self.http.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                )
            }
        )
        self.images_root = Path(DB_PATH) / "images"
        self.noise_patterns = [
            re.compile(r"^resumo$", re.IGNORECASE),
            re.compile(r"^ouvir$", re.IGNORECASE),
            re.compile(r"^deixe seu comentário$", re.IGNORECASE),
            re.compile(r"^[i|l]?\s*\d+([.,]\d+)?\s*[x×]$", re.IGNORECASE),
            re.compile(r"^velocidade( de reprodução)?$", re.IGNORECASE),
            re.compile(r"^continua após a publicidade$", re.IGNORECASE),
            re.compile(r"^comunicar erro$", re.IGNORECASE),
            re.compile(r"^veja também$", re.IGNORECASE),
            re.compile(r"^as mais lidas agora$", re.IGNORECASE),
            re.compile(r"^uol flash$", re.IGNORECASE),
            re.compile(r"^acesse o uol flash$", re.IGNORECASE),
            re.compile(r"^narrativas em disputa$", re.IGNORECASE),
            re.compile(r"^regras de uso do uol\.?$", re.IGNORECASE),
        ]
        self.stop_markers = [
            re.compile(r"^veja também$", re.IGNORECASE),
            re.compile(r"^as mais lidas agora$", re.IGNORECASE),
            re.compile(r"^uol flash$", re.IGNORECASE),
            re.compile(r"^comunicar erro$", re.IGNORECASE),
        ]
        self.blocked_url_patterns = [
            re.compile(r"/playlist/", re.IGNORECASE),
            re.compile(r"/videos?[-/]", re.IGNORECASE),
            re.compile(r"[?&]output=amp", re.IGNORECASE),
        ]

    # ============================================================
    # FILTRO 1: Tamanho mínimo (título + 300 caracteres ou 4 linhas)
    # ============================================================
    def _has_minimum_content(self, titulo: str, conteudo: str) -> bool:
        if not titulo or len(titulo.strip()) < 10:
            return False
        conteudo_limpo = conteudo.strip()
        if len(conteudo_limpo) >= 300:
            return True
        linhas = [l for l in conteudo_limpo.split("\n") if l.strip()]
        if len(linhas) >= 4:
            return True
        return False

    # ============================================================
    # FILTRO 2: Remove lixo (só link, 1 frase, excesso CAPS)
    # ============================================================
    def _is_low_quality(self, titulo: str, conteudo: str) -> bool:
        texto = f"{titulo} {conteudo}".strip()
        if len(texto) < 100:
            return True
        if re.match(r"^https?://\S+$", texto):
            return True
        caps_ratio = sum(1 for c in texto if c.isupper()) / max(len(texto), 1)
        if caps_ratio > 0.5 and len(texto) > 50:
            return True
        return False

    # ============================================================
    # FILTRO 3: Parece notícia? (verbo ou estrutura de manchete)
    # ============================================================
    def _looks_like_news(self, titulo: str) -> bool:
        verbos_noticia = [
            "anuncia", "confirma", "realiza", "lança", "inaugura", "aprova",
            "declara", "afirma", "revela", "divulga", "apresenta", "assina",
            "cria", "muda", "aumenta", "reduz", "cai", "sobe", "cresce",
            "morre", "nasce", "vence", "perde", "fecha", "abre", "bate",
            "aprova", "rejeita", "suspende", "libera", "prende", "investiga",
            "announces", "confirms", "launches", "reveals", "reports", "says",
            "warns", "urges", "claims", "agrees", "signs", "creates",
        ]
        titulo_lower = titulo.lower()
        for verbo in verbos_noticia:
            if verbo in titulo_lower:
                return True
        if re.search(r"[.!?]$", titulo.strip()) or re.search(r"\d+", titulo):
            if len(titulo.split()) >= 5:
                return True
        return False

    def _is_probably_real_image(self, image_url: str) -> bool:
        if not image_url:
            return False
        parsed = urlparse(image_url)
        if parsed.scheme not in ("http", "https"):
            return False
        lowered = image_url.lower()
        if lowered.startswith("data:"):
            return False
        blocked_tokens = ("placeholder", "spacer", "sprite", "blank", "pixel", "logo")
        if any(token in lowered for token in blocked_tokens):
            return False
        if lowered.endswith(".svg") or ".svg?" in lowered:
            return False
        return True

    def _url_is_loadable_image(self, image_url: str) -> bool:
        try:
            head = self.http.head(image_url, timeout=6, allow_redirects=True)
            content_type = (head.headers.get("Content-Type") or "").lower()
            if head.ok and content_type.startswith("image/") and "svg" not in content_type:
                return True
        except Exception:
            pass
        try:
            get_resp = self.http.get(image_url, timeout=8, stream=True, allow_redirects=True)
            content_type = (get_resp.headers.get("Content-Type") or "").lower()
            ok = get_resp.ok and content_type.startswith("image/") and "svg" not in content_type
            get_resp.close()
            return ok
        except Exception:
            return False

    def _extract_full_article(self, url: str, fallback_html: str) -> tuple[str, str, list[str]]:
        if not url:
            clean_fallback = re.sub(r"<[^>]+>", "", fallback_html or "").strip()
            return clean_fallback, "", []
        try:
            resp = self.http.get(url, timeout=12)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            main_candidates = [
                "article", "main article", "main",
                '[itemprop="articleBody"]', ".mc-article-body",
                ".content-text__container", ".entry-content", ".post-content",
            ]
            container = None
            for selector in main_candidates:
                container = soup.select_one(selector)
                if container:
                    break
            if not container:
                container = soup.body
            if not container:
                clean_fallback = re.sub(r"<[^>]+>", "", fallback_html or "").strip()
                return clean_fallback, "", []
            for media_tag in container.select("audio, video, iframe, embed, object, portal"):
                media_tag.decompose()
            for media_tag in container.select("audio source, audio track, video source, video track"):
                media_tag.decompose()
            images: list[str] = []
            for img in container.find_all("img"):
                src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                if not src:
                    srcset = img.get("srcset") or img.get("data-srcset")
                    if srcset:
                        src = srcset.split(",")[0].strip().split(" ")[0]
                if src:
                    img_url = urljoin(url, src)
                    if self._is_probably_real_image(img_url) and self._url_is_loadable_image(img_url):
                        images.append(img_url)
                        img["src"] = img_url
                    else:
                        img.decompose()
                else:
                    img.decompose()
            images = list(dict.fromkeys(images))
            article_html = str(container)
            article_text = container.get_text("\n", strip=True)
            article_text = re.sub(r"\n{3,}", "\n\n", article_text).strip()
            return article_text, article_html, images
        except HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code in (403, 404, 410):
                self.logger.warning(
                    "link da materia indisponivel; usando fallback do feed",
                    extra={"context": {"url": url, "status_code": status_code}},
                )
            else:
                self.logger.exception(
                    "falha http ao extrair html completo da materia",
                    extra={"context": {"url": url, "status_code": status_code}},
                )
            clean_fallback = re.sub(r"<[^>]+>", "", fallback_html or "").strip()
            return clean_fallback, "", []
        except Exception:
            self.logger.exception(
                "falha ao extrair html completo da materia", extra={"context": {"url": url}}
            )
            clean_fallback = re.sub(r"<[^>]+>", "", fallback_html or "").strip()
            return clean_fallback, "", []

    def _safe_news_id(self, raw_id: str) -> str:
        safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", raw_id or "sem_id").strip("_")
        return safe[:80] or "sem_id"

    def _safe_folder_name(self, value: str, fallback: str = "desconhecido") -> str:
        safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", (value or "").strip()).strip("._-")
        if not safe:
            safe = fallback
        return safe[:80]

    def _guess_extension(self, image_url: str, content_type: str) -> str:
        if "jpeg" in content_type or "jpg" in content_type:
            return ".jpg"
        if "png" in content_type:
            return ".png"
        if "webp" in content_type:
            return ".webp"
        if "gif" in content_type:
            return ".gif"
        path = urlparse(image_url).path.lower()
        if "." in path:
            candidate = "." + path.split(".")[-1]
            if candidate in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                return ".jpg" if candidate == ".jpeg" else candidate
        return ".jpg"

    def _download_images(self, news_id: str, image_urls: list[str], source_type: str,
                         source_name: str, published: datetime) -> list[str]:
        if not image_urls:
            return []
        safe_id = self._safe_news_id(news_id)
        source_folder = self._safe_folder_name(source_type, "rss")
        date_folder = published.date().isoformat()
        name_folder = self._safe_folder_name(source_name, "fonte")
        target_dir = self.images_root / source_folder / date_folder / name_folder / safe_id
        target_dir.mkdir(parents=True, exist_ok=True)
        local_paths: list[str] = []
        for idx, image_url in enumerate(image_urls[:10], start=1):
            try:
                resp = self.http.get(image_url, timeout=12, stream=True, allow_redirects=True)
                content_type = (resp.headers.get("Content-Type") or "").lower()
                if not (resp.ok and content_type.startswith("image/") and "svg" not in content_type):
                    resp.close()
                    continue
                ext = self._guess_extension(image_url, content_type)
                file_name = f"img_{idx:02d}{ext}"
                file_path = target_dir / file_name
                with file_path.open("wb") as fh:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)
                resp.close()
                local_paths.append(os.path.relpath(file_path, Path.cwd()).replace("\\", "/"))
            except Exception:
                self.logger.exception(
                    "falha ao baixar imagem da noticia",
                    extra={"context": {"news_id": news_id, "image_url": image_url}},
                )
        return local_paths

    def _clean_article_text(self, raw: str) -> str:
        lines = [line.strip() for line in re.split(r"\n+", raw or "") if line.strip()]
        cleaned: list[str] = []
        for line in lines:
            if any(rx.search(line) for rx in self.stop_markers):
                break
            if any(rx.search(line) for rx in self.noise_patterns):
                continue
            if len(line) < 70 and re.search(r"^(marco|aline|alicia|coluna|opinião)", line, re.IGNORECASE):
                continue
            cleaned.append(line)
        return "\n".join(cleaned).strip()

    def _resolve_google_news_link(self, link: str) -> str:
        if not link:
            return link
        host = urlparse(link).netloc.lower()
        if "news.google.com" not in host:
            return link
        try:
            resp = self.http.get(link, timeout=12, allow_redirects=True)
            final_url = resp.url or link
            final_host = urlparse(final_url).netloc.lower()
            if final_url and "news.google.com" not in final_host:
                return final_url
            parsed = urlparse(link)
            params = parse_qs(parsed.query)
            for key in ("url", "u", "q"):
                value = params.get(key, [None])[0]
                if value and value.startswith("http"):
                    return value
        except Exception:
            self.logger.exception(
                "falha ao resolver link do google news", extra={"context": {"url": link}}
            )
        return link

    def _should_skip_url(self, url: str) -> bool:
        if not url:
            return True
        lower_url = url.lower()
        return any(pattern.search(lower_url) for pattern in self.blocked_url_patterns)

    def collect_source(self, source: RSSSourceConfig) -> int:
        self.logger.info("coleta rss iniciada", extra={"context": {"source_name": source.name, "url": source.url}})
        try:
            feed = feedparser.parse(source.url)
            if not getattr(feed, "entries", None):
                self.logger.info("fonte rss sem entradas", extra={"context": {"source_name": source.name}})
                return 0
            saved = 0
            for entry in feed.entries[:30]:
                entry_id = entry.get("id", entry.get("link", ""))
                if not entry_id:
                    continue
                news_id = f"rss_{entry_id[:200]}"
                published = datetime.now(dt_timezone.utc)
                if getattr(entry, "published_parsed", None):
                    published = datetime(
                        entry.published_parsed.tm_year, entry.published_parsed.tm_mon,
                        entry.published_parsed.tm_mday, entry.published_parsed.tm_hour,
                        entry.published_parsed.tm_min, entry.published_parsed.tm_sec,
                        tzinfo=dt_timezone.utc,
                    )
                elif getattr(entry, "updated_parsed", None):
                    published = datetime(
                        entry.updated_parsed.tm_year, entry.updated_parsed.tm_mon,
                        entry.updated_parsed.tm_mday, entry.updated_parsed.tm_hour,
                        entry.updated_parsed.tm_min, entry.updated_parsed.tm_sec,
                        tzinfo=dt_timezone.utc,
                    )
                feed_content = ""
                if getattr(entry, "content", None):
                    feed_content = entry.content[0].get("value", "")
                elif entry.get("summary"):
                    feed_content = entry.get("summary", "")
                elif entry.get("description"):
                    feed_content = entry.get("description", "")
                source_url = self._resolve_google_news_link(entry.get("link", ""))
                if self._should_skip_url(source_url):
                    continue
                full_text, full_html, images = self._extract_full_article(source_url, feed_content)
                cleaned_full_text = self._clean_article_text(full_text)
                cleaned_feed_content = self._clean_article_text(re.sub(r"<[^>]+>", "", feed_content).strip())
                if not cleaned_full_text and not cleaned_feed_content:
                    continue
                titulo = entry.get("title", "Sem titulo")
                conteudo_final = cleaned_full_text or cleaned_feed_content
                if not self._has_minimum_content(titulo, conteudo_final):
                    continue
                if self._is_low_quality(titulo, conteudo_final):
                    continue
                if not self._looks_like_news(titulo):
                    continue
                local_images = self._download_images(
                    news_id=news_id, image_urls=images, source_type="rss",
                    source_name=source.name, published=published,
                )
                documento = self.tinydb.salvar_noticia({
                    "id": news_id, "titulo": titulo[:500], "conteudo": cleaned_full_text,
                    "conteudo_html": full_html, "imagens": images, "imagens_local": local_images,
                    "conteudo_feed": cleaned_feed_content, "fonte": "rss", "url": source_url,
                    "autor": entry.get("author", source.name)[:255],
                    "data_publicacao": published.isoformat(), "score": 0, "comentarios": 0,
                    "palavras_chave": [], "relevancia": 0, "feed_name": source.name,
                })
                if documento:
                    saved += 1
            self.logger.info("coleta rss finalizada", extra={"context": {"source_name": source.name, "saved": saved}})
            return saved
        except Exception as exc:
            self.logger.exception("excecao na coleta rss", extra={"context": {"source_name": source.name, "error": str(exc)}})
            return 0

    def run(self, sources: list[RSSSourceConfig]) -> int:
        active_sources = [s for s in sources if s.is_active]
        if not active_sources:
            self.logger.info("sem fontes rss ativas")
            return 0
        total = 0
        for source in active_sources:
            total += self.collect_source(source)
            time.sleep(0.2)
        return total