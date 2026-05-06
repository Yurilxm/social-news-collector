"""
Coletor do X/Twitter via API oficial.
Estrutura pronta - Aguardando Bearer Token para ativar.
"""

import os
import logging
from datetime import datetime, timezone as dt_timezone
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("twitter_collector")


class TwitterCollector:
    def __init__(self) -> None:
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self.is_active = bool(self.bearer_token)
        self.stats = {"accounts_checked": 0, "tweets_collected": 0, "errors": 0}

    def collect(self, username: str, limit: int = 20) -> int:
        if not self.is_active:
            print(f"   Twitter nao configurado - pulando @{username}")
            return 0
        print(f"   Twitter: @{username} ({limit} tweets)")
        try:
            import tweepy
            client = tweepy.Client(bearer_token=self.bearer_token, wait_on_rate_limit=True)
            user = client.get_user(username=username)
            if not user.data:
                return 0
            tweets = client.get_users_tweets(id=user.data.id, max_results=min(limit, 100),
                                             tweet_fields=['created_at', 'text', 'public_metrics'])
            if not tweets.data:
                return 0
            saved = 0
            for tweet in tweets.data:
                print(f"   Novo tweet de @{username}: {tweet.text[:60]}...")
                saved += 1
            self.stats["tweets_collected"] += saved
            self.stats["accounts_checked"] += 1
            return saved
        except Exception as e:
            logger.error(f"Erro ao coletar tweets de @{username}: {e}")
            self.stats["errors"] += 1
            return 0