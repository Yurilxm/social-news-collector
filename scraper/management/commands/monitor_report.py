from django.core.management.base import BaseCommand
from scraper.models import FilteredPost, MonitorConfig
from django.db.models import Count, Avg
from datetime import datetime, timedelta
from django.utils import timezone

class Command(BaseCommand):
    help = "Relatório de monitoramento"

    def add_arguments(self, parser):
        parser.add_argument('--hours', type=int, default=24, help='Últimas X horas')

    def handle(self, *args, **kwargs):
        hours = kwargs['hours']
        since = timezone.now() - timedelta(hours=hours)
        
        self.stdout.write(self.style.WARNING(f"""
╔══════════════════════════════════════╗
║     RELATÓRIO DE MONITORAMENTO     ║
╠══════════════════════════════════════╣
║ Período: últimas {hours}h{'':>16} ║
╚══════════════════════════════════════╝
        """))
        
        # Posts por monitor
        posts_by_monitor = FilteredPost.objects.filter(
            collected_at__gte=since
        ).values('monitor__name').annotate(
            total=Count('id'),
            avg_relevance=Avg('relevance_score')
        ).order_by('-total')
        
        self.stdout.write("\n📊 POSTS POR MONITOR:")
        self.stdout.write("-" * 50)
        for item in posts_by_monitor:
            self.stdout.write(
                f"  {item['monitor__name']}: {item['total']} posts "
                f"(relevância média: {item['avg_relevance']:.1f})"
            )
        
        # Top posts
        top_posts = FilteredPost.objects.filter(
            collected_at__gte=since
        ).select_related('reddit_post').order_by('-relevance_score')[:5]
        
        self.stdout.write("\n🏆 TOP 5 POSTS MAIS RELEVANTES:")
        self.stdout.write("-" * 50)
        for i, fp in enumerate(top_posts, 1):
            self.stdout.write(
                f"{i}. [{fp.relevance_score:.1f}] {fp.reddit_post.title[:100]}"
            )
            self.stdout.write(f"   👍 {fp.reddit_post.score} | r/{fp.reddit_post.subreddit}")