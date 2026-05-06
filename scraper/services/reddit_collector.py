import logging
import re
import time
from datetime import datetime, timezone as dt_timezone
import requests
from .tinydb_service import TinyDBService

logger = logging.getLogger("reddit_collector")


class RedditCollector:
    def __init__(self) -> None:
        self.tinydb = TinyDBService()
        self.headers = {
            "User-Agent": "SocialNewsCollector/1.0",
            "Accept": "application/json",
        }

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

    def _looks_like_news(self, titulo: str, conteudo: str) -> bool:
        titulo_lower = titulo.lower()
        rejeitar = [
            "o que vocês acham", "o que voce acha", "oq vcs acham",
            "será que", "alguém sabe", "alguem sabe", "me ajudem",
            "isso é absurdo", "olha isso", "vejam isso", "ganhei",
        ]
        for padrao in rejeitar:
            if padrao in titulo_lower:
                return False
        verbos_noticia = [
            "anuncia", "confirma", "realiza", "lança", "inaugura", "aprova",
            "declara", "afirma", "revela", "divulga", "apresenta", "assina",
            "cria", "muda", "aumenta", "reduz", "cai", "sobe", "cresce",
            "morre", "nasce", "vence", "perde", "fecha", "abre", "bate",
            "suspende", "libera", "prende", "investiga", "diz", "dizem",
            "informa", "explica", "acusam", "denuncia", "pede", "propõe",
        ]
        for verbo in verbos_noticia:
            if verbo in titulo_lower:
                return True
        if ":" in titulo and len(titulo.split()) >= 5:
            return True
        if len(conteudo.strip()) >= 500:
            return True
        if re.search(r"\d+", titulo) and len(titulo.split()) >= 3:
            return True
        if not titulo_lower.strip().endswith("?") and len(titulo.split()) >= 5:
            return True
        return False

    def _calculate_relevance(self, titulo: str, conteudo: str, keywords: list[str]) -> float:
        if not keywords:
            return 1.0
        score = 0.0
        titulo_lower = titulo.lower()
        conteudo_lower = conteudo.lower()
        for kw in keywords:
            kw_lower = kw.lower().strip()
            if not kw_lower:
                continue
            if kw_lower in titulo_lower:
                score += 3.0
            elif kw_lower in conteudo_lower:
                score += 1.0
        return score

    def _should_save(self, titulo: str, conteudo: str, keywords: list[str]) -> tuple[bool, float]:
        if not self._has_minimum_content(titulo, conteudo):
            return False, 0.0
        if self._is_low_quality(titulo, conteudo):
            return False, 0.0
        if not self._looks_like_news(titulo, conteudo):
            return False, 0.0
        relevance = self._calculate_relevance(titulo, conteudo, keywords)
        return True, relevance

    def collect(self, target: str, monitor_type: str = "subreddit", limit: int = 30,
                min_score: int = 10, keywords: str = "") -> int:
        if monitor_type == "subreddit":
            url = f"https://www.reddit.com/r/{target}/new.json"
        else:
            url = f"https://www.reddit.com/user/{target}/submitted.json"
        params = {"limit": limit}
        keywords_list = [k.strip() for k in keywords.split(",") if k.strip()]
        saved = 0
        try:
            print(f"   Acessando: {url}")
            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            if response.status_code != 200:
                print(f"   Erro HTTP: {response.status_code}")
                return 0
            items = response.json().get("data", {}).get("children", [])
            for item in items:
                post = item.get("data", {})
                if post.get("stickied", False):
                    continue
                score = int(post.get("score", 0))
                if score < min_score:
                    continue
                titulo = post.get("title", "")
                conteudo = post.get("selftext") or ""
                should_save, relevance = self._should_save(titulo, conteudo, keywords_list)
                if not should_save:
                    continue
                created_at = datetime.fromtimestamp(post["created_utc"], tz=dt_timezone.utc)
                imagem_url = ""
                thumbnail = post.get("thumbnail", "")
                if thumbnail and thumbnail.startswith("http"):
                    imagem_url = thumbnail
                documento = self.tinydb.salvar_noticia({
                    "id": f"reddit_{post['id']}",
                    "titulo": titulo,
                    "conteudo": conteudo,
                    "fonte": "reddit",
                    "url": f"https://reddit.com{post.get('permalink', '')}",
                    "autor": post.get("author", "[deleted]"),
                    "data_publicacao": created_at.isoformat(),
                    "score": score,
                    "comentarios": int(post.get("num_comments", 0)),
                    "palavras_chave": keywords_list,
                    "relevancia": relevance,
                    "subreddit": post.get("subreddit", target),
                    "imagem_url": imagem_url,
                    "thumbnail": thumbnail,
                })
                if documento:
                    saved += 1
                time.sleep(0.1)
        except Exception as e:
            logger.error(f"Erro ao coletar {target}: {e}")
        return saved