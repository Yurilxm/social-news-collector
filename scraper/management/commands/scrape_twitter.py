from django.core.management.base import BaseCommand
from scraper.services.twitter_scraper import scrape_user_tweets
from datetime import datetime
import sys

class Command(BaseCommand):
    help = "Coleta tweets de forma resiliente com múltiplas tentativas"

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Nome da conta (sem @)')
        parser.add_argument('--limit', type=int, default=20, help='Número de tweets')
        parser.add_argument('--retries', type=int, default=3, help='Tentativas máximas')

    def handle(self, *args, **kwargs):
        username = kwargs['username'].strip('@')
        limit = kwargs['limit']
        max_retries = kwargs['retries']
        
        # Banner
        self.stdout.write(self.style.WARNING("""
╔══════════════════════════════════════╗
║     TWITTER SCRAPER RESILIENTE     ║
╚══════════════════════════════════════╝
        """))
        
        self.stdout.write(f"🎯 Alvo: @{username}")
        self.stdout.write(f"📊 Limite: {limit} tweets")
        self.stdout.write(f"🔄 Máximo de tentativas: {max_retries}")
        self.stdout.write(f"🕐 Início: {datetime.now().strftime('%H:%M:%S')}")
        self.stdout.write("-" * 50)
        
        try:
            inicio = datetime.now()
            
            # Executa coleta
            tweets = scrape_user_tweets(username, limit, max_retries)
            
            # Calcula tempo
            tempo = (datetime.now() - inicio).total_seconds()
            
            # Resume resultados
            self.stdout.write("\n" + "=" * 50)
            self.stdout.write(self.style.SUCCESS("📊 RESUMO DA COLETA"))
            self.stdout.write("=" * 50)
            self.stdout.write(f"⏱️  Tempo total: {tempo:.1f} segundos")
            self.stdout.write(f"✅ Tweets novos: {len(tweets)}")
            self.stdout.write(f"🎯 Conta: @{username}")
            
            if tweets:
                self.stdout.write(f"\n📋 Último tweet coletado:")
                self.stdout.write(f"   {tweets[-1].content[:100]}...")
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\n\n⏹️ Coleta cancelada pelo usuário"))
            sys.exit(0)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Erro fatal: {e}"))
            sys.exit(1)