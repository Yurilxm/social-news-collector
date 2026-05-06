import logging
import os
from datetime import datetime
from tinydb import Query, TinyDB

DB_PATH = os.path.join(os.getcwd(), "db")
logger = logging.getLogger("bot.tinydb")

KEYWORDS_POR_CIDADE = {
    "cabo_frio": ["cabo frio", "cabofrio", "praia do forte", "pero", "sao cristovao"],
    "buzios": ["buzios", "rua das pedras", "geriba", "ferradura"],
    "arraial_do_cabo": ["arraial do cabo", "arraial", "pontal", "prainha", "forno"],
    "araruama": ["araruama", "lagoa de araruama", "praia seca"],
    "saquarema": ["saquarema", "itauna", "vila", "bacaxa"],
    "sao_pedro_da_aldeia": ["sao pedro da aldeia", "sao pedro"],
    "iguaba_grande": ["iguaba grande", "iguaba"],
}


class TinyDBService:
    def __init__(self) -> None:
        os.makedirs(DB_PATH, exist_ok=True)
        self.db_noticias = TinyDB(os.path.join(DB_PATH, "noticias.json"))
        self.db_reddit = TinyDB(os.path.join(DB_PATH, "reddit.json"))
        self.db_rss = TinyDB(os.path.join(DB_PATH, "rss.json"))
        self.db_logs = TinyDB(os.path.join(DB_PATH, "logs.json"))
        self.stats = {"salvos": 0, "duplicados": 0, "erros": 0}

    def detectar_regiao(self, texto: str, keywords_monitor: list[str] | None = None) -> dict:
        texto_lower = texto.lower()
        for cidade_key, keywords in KEYWORDS_POR_CIDADE.items():
            for kw in keywords:
                if kw in texto_lower:
                    return {
                        "regiao": "Regiao dos Lagos",
                        "cidade": cidade_key.replace("_", " ").title(),
                        "match": kw,
                    }
        if keywords_monitor:
            for kw in keywords_monitor:
                if kw.lower() in texto_lower:
                    for cidade_key, cidade_kws in KEYWORDS_POR_CIDADE.items():
                        if kw.lower() in cidade_kws:
                            return {
                                "regiao": "Regiao dos Lagos",
                                "cidade": cidade_key.replace("_", " ").title(),
                                "match": kw,
                            }
        return {"regiao": "Nacional", "cidade": None, "match": None}

    def salvar_noticia(self, dados: dict) -> dict | None:
        try:
            noticia = Query()
            if self.db_noticias.search(noticia.id == dados["id"]):
                self.stats["duplicados"] += 1
                return None
            texto_busca = f"{dados.get('titulo', '')} {dados.get('conteudo', '')}"
            regiao_info = self.detectar_regiao(texto_busca, dados.get("palavras_chave", []))
            documento = {
                "id": dados["id"],
                "titulo": dados.get("titulo", ""),
                "conteudo": dados.get("conteudo", ""),
                "fonte": dados.get("fonte", "desconhecida"),
                "url": dados.get("url", ""),
                "autor": dados.get("autor", ""),
                "data_publicacao": dados.get("data_publicacao", datetime.now().isoformat()),
                "data_coleta": datetime.now().isoformat(),
                "score": dados.get("score", 0),
                "comentarios": dados.get("comentarios", 0),
                "palavras_chave": dados.get("palavras_chave", []),
                "relevancia": dados.get("relevancia", 0),
                "regiao": regiao_info["regiao"],
                "cidade": regiao_info["cidade"],
                "match_regiao": regiao_info["match"],
                "subreddit": dados.get("subreddit", ""),
                "feed_name": dados.get("feed_name", ""),
                "imagem_url": dados.get("imagem_url", ""),
                "thumbnail": dados.get("thumbnail", ""),
            }
            self.db_noticias.insert(documento)
            if dados.get("fonte") == "reddit":
                self.db_reddit.insert(documento)
            elif dados.get("fonte") == "rss":
                self.db_rss.insert(documento)
            self.stats["salvos"] += 1
            return documento
        except Exception:
            logger.exception("falha ao salvar noticia no tinydb")
            self.stats["erros"] += 1
            return None

    def get_stats(self) -> dict:
        return {
            "total_noticias": len(self.db_noticias),
            "total_reddit": len(self.db_reddit),
            "total_rss": len(self.db_rss),
            "por_regiao": self.contar_por_regiao(),
            "por_cidade": self.contar_por_cidade(),
        }

    def contar_por_regiao(self) -> dict:
        contagem: dict[str, int] = {}
        for item in self.db_noticias.all():
            regiao = item.get("regiao", "Desconhecida")
            contagem[regiao] = contagem.get(regiao, 0) + 1
        return contagem

    def contar_por_cidade(self) -> dict:
        contagem: dict[str, int] = {}
        for item in self.db_noticias.all():
            cidade = item.get("cidade")
            if cidade:
                contagem[cidade] = contagem.get(cidade, 0) + 1
        return contagem

    def registrar_log(self, mensagem: str, tipo: str = "info", dados: dict | None = None) -> None:
        self.db_logs.insert({
            "timestamp": datetime.now().isoformat(),
            "tipo": tipo,
            "mensagem": mensagem,
            "dados": dados or {},
        })

    def clear_all_data(self, include_logs: bool = True) -> dict:
        removed = {
            "noticias": len(self.db_noticias),
            "reddit": len(self.db_reddit),
            "rss": len(self.db_rss),
            "logs": len(self.db_logs) if include_logs else 0,
        }
        self.db_noticias.truncate()
        self.db_reddit.truncate()
        self.db_rss.truncate()
        if include_logs:
            self.db_logs.truncate()
        self.stats = {"salvos": 0, "duplicados": 0, "erros": 0}
        return removed