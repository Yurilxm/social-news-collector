from django.core.management.base import BaseCommand
from scraper.services.threads_scraper import scrape_threads_posts
from datetime import datetime

class Command(BaseCommand):
    help = "Testa coleta de posts do Threads (Meta)"

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Nome da conta sem @')
        parser.add_argument('--limit', type=int, default=10, help='Número de posts')

    def handle(self, *args, **kwargs):
        username = kwargs['username'].strip('@')
        limit = kwargs['limit']
        
        self.stdout.write(self.style.WARNING(f"""
╔══════════════════════════════════════╗
║     THREADS SCRAPER (Meta)         ║
╠══════════════════════════════════════╣
║ Conta: @{username:<25} ║
║ Limite: {limit} posts{'':>17} ║
║ Hora: {datetime.now().strftime('%H:%M:%S')}{'':>20} ║
╚══════════════════════════════════════╝
        """))
        
        try:
            inicio = datetime.now()
            posts = scrape_threads_posts(username, limit)
            tempo = (datetime.now() - inicio).total_seconds()
            
            if posts:
                self.stdout.write(
                    self.style.SUCCESS(f"\n✅ Coleta concluída em {tempo:.1f}s!")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"\n⚠️ Threads bloqueou scraping ({tempo:.1f}s)")
                )
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Erro: {e}"))