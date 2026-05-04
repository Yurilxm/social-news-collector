from django.core.management.base import BaseCommand
from scraper.services.monitor_service import RedditMonitor
from scraper.models import MonitorConfig

class Command(BaseCommand):
    help = "Executa ciclo de monitoramento uma vez"

    def handle(self, *args, **kwargs):
        monitors = MonitorConfig.objects.filter(is_active=True)
        
        if not monitors.exists():
            self.stdout.write(self.style.ERROR(
                "❌ Nenhum monitor configurado!\n"
                "Use: python manage.py monitor_setup"
            ))
            return
        
        monitor_service = RedditMonitor()
        total = monitor_service.run_all_active_monitors()
        
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Monitoramento concluído! {total} posts encontrados"
        ))