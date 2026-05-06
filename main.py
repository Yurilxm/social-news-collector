import json
import logging
import os
import sys
import time
from pathlib import Path

from scraper.services.reddit_collector import RedditCollector
from scraper.services.rss_collector import RSSCollector, RSSSourceConfig
from scraper.services.tinydb_service import TinyDBService
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")

CONFIG_PATH = Path("config/bot_config.json")


def load_config():
    if not CONFIG_PATH.exists():
        logger.error(f"Arquivo de configuracao nao encontrado: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run_once():
    config = load_config()
    tinydb = TinyDBService()
    
    logger.info("=" * 60)
    logger.info("INICIANDO CICLO DE COLETA")
    logger.info("=" * 60)
    
    # Reddit
    reddit_monitors = config.get("reddit_monitors", [])
    if reddit_monitors:
        logger.info(f"Reddit: {len(reddit_monitors)} monitores")
        rc = RedditCollector()
        for monitor in reddit_monitors:
            if not monitor.get("is_active", True):
                continue
            total = rc.collect(
                target=monitor["target"],
                monitor_type=monitor.get("monitor_type", "subreddit"),
                limit=monitor.get("limit", 30),
                min_score=monitor.get("min_score", 10),
                keywords=monitor.get("keywords", ""),
            )
            logger.info(f"  {monitor['name']}: {total} posts salvos")
    
    # RSS
    rss_sources = config.get("rss_sources", [])
    if rss_sources:
        logger.info(f"RSS: {len(rss_sources)} fontes")
        rss = RSSCollector()
        for source in rss_sources:
            if not source.get("is_active", True):
                continue
            total = rss.collect_source(RSSSourceConfig(source["name"], source["url"]))
            logger.info(f"  {source['name']}: {total} entradas salvas")
    
    # Estatisticas
    stats = tinydb.get_stats()
    logger.info("=" * 60)
    logger.info("RESUMO")
    logger.info(f"  Total noticias: {stats['total_noticias']}")
    logger.info(f"  Reddit: {stats['total_reddit']} | RSS: {stats['total_rss']}")
    logger.info(f"  Por regiao: {stats['por_regiao']}")
    if stats['por_cidade']:
        logger.info(f"  Por cidade: {stats['por_cidade']}")
    logger.info("=" * 60)


def run_loop():
    interval = load_config().get("interval_minutes", 5)
    logger.info(f"Scheduler iniciado - ciclo a cada {interval} minutos")
    while True:
        run_once()
        logger.info(f"Proximo ciclo em {interval} minutos...")
        time.sleep(interval * 60)


def view_news(limit=10, source=None, term=None):
    tinydb = TinyDBService()
    items = tinydb.db_noticias.all()
    if source:
        items = [i for i in items if i.get("fonte") == source]
    if term:
        t = term.lower()
        items = [i for i in items if t in i.get("titulo", "").lower() or t in i.get("conteudo", "").lower()]
    items.sort(key=lambda i: i.get("data_publicacao", ""), reverse=True)
    items = items[:limit]
    
    print(f"\n{'='*100}")
    print(f"{'#':<4} {'FONTE':<8} {'DATA':<16} {'SCORE':<6} {'TITULO':<50} {'AUTOR':<20}")
    print("-"*100)
    for idx, n in enumerate(items, 1):
        data = n.get("data_publicacao", "")[:16].replace("T", " ")
        print(f"{idx:<4} {n.get('fonte','?'):<8} {data:<16} {n.get('score',0):<6} {n.get('titulo','')[:48]:<50} {str(n.get('autor',''))[:18]:<20}")
    print("="*100)
    print(f"Total exibido: {len(items)}")


def clear_data():
    tinydb = TinyDBService()
    removed = tinydb.clear_all_data()
    print(f"Dados removidos: noticias={removed['noticias']}, reddit={removed['reddit']}, rss={removed['rss']}, logs={removed['logs']}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Social News Collector")
    parser.add_argument("command", nargs="?", default="run-once",
                        choices=["run-once", "run-loop", "view-news", "clear-data"])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--source", choices=["reddit", "rss"])
    parser.add_argument("--term")
    args = parser.parse_args()
    
    if args.command == "run-once":
        run_once()
    elif args.command == "run-loop":
        run_loop()
    elif args.command == "view-news":
        view_news(args.limit, args.source, args.term)
    elif args.command == "clear-data":
        clear_data()