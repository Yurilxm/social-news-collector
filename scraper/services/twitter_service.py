"""
Serviço de coleta do X/Twitter
Estrutura pronta - Aguardando API key para ativar

Para ativar:
1. Obter Bearer Token em https://developer.twitter.com
2. Adicionar TWITTER_BEARER_TOKEN no .env
3. Executar o scheduler normalmente
"""

import os
import logging
from datetime import datetime, timezone as dt_timezone
from django.utils import timezone
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class TwitterMonitor:
    """Monitor do X/Twitter - Coleta tweets via API oficial"""
    
    def __init__(self):
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.is_active = bool(self.bearer_token)
        self.stats = {
            'accounts_checked': 0,
            'tweets_collected': 0,
            'errors': 0,
        }
    
    def get_client(self):
        """Inicializa cliente da API oficial do X/Twitter"""
        if not self.bearer_token:
            raise ValueError("TWITTER_BEARER_TOKEN não configurado no .env")
        
        import tweepy
        return tweepy.Client(
            bearer_token=self.bearer_token,
            wait_on_rate_limit=True
        )
    
    def collect_tweets(self, username, limit=20):
        """Coleta tweets de um perfil"""
        if not self.is_active:
            print(f"   ⚠️  Twitter não configurado - pulando @{username}")
            return 0
        
        print(f"   📡 Twitter: @{username} ({limit} tweets)")
        
        try:
            client = self.get_client()
            user = client.get_user(username=username)
            
            if not user.data:
                print(f"   ⚠️  Usuário @{username} não encontrado")
                return 0
            
            tweets = client.get_users_tweets(
                id=user.data.id,
                max_results=min(limit, 100),
                tweet_fields=['created_at', 'text', 'public_metrics']
            )
            
            if not tweets.data:
                return 0
            
            # Salva no banco de dados
            from scraper.models import Tweet
            
            saved = 0
            for tweet in tweets.data:
                _, created = Tweet.objects.get_or_create(
                    tweet_id=str(tweet.id),
                    defaults={
                        'username': username,
                        'content': tweet.text,
                        'date': tweet.created_at,
                        'url': f'https://twitter.com/{username}/status/{tweet.id}',
                    }
                )
                if created:
                    saved += 1
            
            self.stats['tweets_collected'] += saved
            self.stats['accounts_checked'] += 1
            print(f"   ✅ {saved} novos tweets de @{username}")
            return saved
            
        except Exception as e:
            logger.error(f"Erro ao coletar tweets de @{username}: {e}")
            self.stats['errors'] += 1
            return 0
    
    def run_all_accounts(self):
        """Executa coleta em todas as contas configuradas"""
        if not self.is_active:
            print("📡 Twitter: estrutura pronta (aguardando API key)")
            return 0
        
        from scraper.models import MonitorConfig
        
        accounts = MonitorConfig.objects.filter(
            monitor_type='twitter',
            is_active=True
        )
        
        if not accounts.exists():
            print("📡 Twitter: nenhuma conta configurada")
            return 0
        
        total = 0
        for account in accounts:
            total += self.collect_tweets(account.target, limit=30)
        
        return total