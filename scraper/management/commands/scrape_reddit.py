from django.core.management.base import BaseCommand
from scraper.services.reddit_scraper import scrape_reddit_posts
from datetime import datetime

class Command(BaseCommand):
    help = "Coleta posts do Reddit de subreddits de notícias"

    def add_arguments(self, parser):
        parser.add_argument('subreddit', type=str, help='Nome do subreddit (sem r/)')
        parser.add_argument(
            '--limit',
            type=int,
            default=25,
            help='Número de posts (padrão: 25)'
        )

    def handle(self, *args, **kwargs):
        subreddit = kwargs['subreddit'].strip('r/').strip('/')
        limit = kwargs['limit']
        
        self.stdout.write(self.style.WARNING(f"""
╔══════════════════════════════════════╗
║     REDDIT SCRAPER - Notícias      ║
╠══════════════════════════════════════╣
║ Subreddit: r/{subreddit:<21} ║
║ Limite: {limit} posts{'':>17} ║
║ Hora: {datetime.now().strftime('%H:%M:%S')}{'':>20} ║
╚══════════════════════════════════════╝
        """))
        
        try:
            inicio = datetime.now()
            
            # Coleta posts
            posts = scrape_reddit_posts(subreddit, limit)
            
            tempo = (datetime.now() - inicio).total_seconds()
            
            if posts:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✅ Coleta concluída em {tempo:.1f}s!"
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"📊 {len(posts)} posts coletados de r/{subreddit}"
                    )
                )
                
                # Mostra top 3
                self.stdout.write("\n🏆 Top 3 por pontuação:")
                top_posts = sorted(posts, key=lambda x: x.score, reverse=True)[:3]
                for i, post in enumerate(top_posts, 1):
                    self.stdout.write(
                        f"{i}. [{post.score}👍] {post.title[:100]}"
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"\n⚠️ Nenhum post novo encontrado"
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"\n❌ Erro: {e}")
            )