from django.core.management.base import BaseCommand
from scraper.services.rss_service import RSSMonitor

class Command(BaseCommand):
    help = "Executa coleta de feeds RSS"

    def handle(self, *args, **kwargs):
        rss_monitor = RSSMonitor()
        total = rss_monitor.run_all_feeds()
        
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Coleta RSS concluída! {total} novas entradas"
        ))