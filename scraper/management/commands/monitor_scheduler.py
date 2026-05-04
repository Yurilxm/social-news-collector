import schedule
import time
import signal
import sys
from django.core.management.base import BaseCommand
from scraper.services.monitor_service import RedditMonitor
from scraper.services.rss_service import RSSMonitor
from scraper.models import MonitorConfig, RSSSource
from datetime import datetime

class Command(BaseCommand):
    help = "Serviço contínuo de monitoramento (Reddit + RSS a cada 5 min)"

    def __init__(self):
        super().__init__()
        self.running = True
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        self.stdout.write(self.style.WARNING("\n\n⏹️ Parando scheduler..."))
        self.stdout.write(self.style.SUCCESS("✅ Sistema finalizado com segurança"))
        self.running = False
        sys.exit(0)

    def job(self):
        """Job único que executa Reddit + RSS"""
        ciclo = datetime.now().strftime('%H:%M:%S')
        
        print(f"\n{'='*60}")
        print(f"🔄 CICLO AUTOMÁTICO - {ciclo}")
        print(f"{'='*60}")
        
        # ==================== REDDIT ====================
        print(f"\n🔍 REDDIT")
        print(f"{'-'*40}")
        try:
            monitor_service = RedditMonitor()
            total_reddit = monitor_service.run_all_active_monitors()
            self.stdout.write(
                self.style.SUCCESS(f"✅ Reddit: {total_reddit} posts relevantes")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Reddit: {e}")
            )
        
        # ==================== RSS ====================
        print(f"\n📡 RSS")
        print(f"{'-'*40}")
        try:
            rss_monitor = RSSMonitor()
            total_rss = rss_monitor.run_all_feeds()
            self.stdout.write(
                self.style.SUCCESS(f"✅ RSS: {total_rss} novas entradas")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ RSS: {e}")
            )
        
        # ==================== RESUMO ====================
        print(f"\n{'='*60}")
        print(f"⏱️ Próximo ciclo: em 5 minutos")
        print(f"🕐 Previsão: {(datetime.now().replace(second=0, microsecond=0))}")
        print(f"{'='*60}\n")

    def handle(self, *args, **kwargs):
        # Verifica se tem fontes configuradas
        reddit_count = MonitorConfig.objects.filter(is_active=True).count()
        rss_count = RSSSource.objects.filter(is_active=True).count()
        
        if reddit_count == 0 and rss_count == 0:
            self.stdout.write(self.style.ERROR(
                "❌ Nenhuma fonte configurada!\n"
                "Use: python manage.py monitor_setup && python manage.py rss_setup"
            ))
            return
        
        # Banner inicial
        self.stdout.write(self.style.SUCCESS(f"""
╔══════════════════════════════════════════╗
║     SCHEDULER AUTOMÁTICO - 5 MIN      ║
╠══════════════════════════════════════════╣
║ 🔍 Reddit: {reddit_count} monitores ativos{'':>15} ║
║ 📡 RSS: {rss_count} fontes ativas{'':>18} ║
║ ⏱️  Intervalo: 5 minutos{'':>17} ║
║ 🕐 Início: {datetime.now().strftime('%H:%M:%S')}{'':>18} ║
╚══════════════════════════════════════════╝
        """))
        
        # Agenda ÚNICO job a cada 5 minutos
        schedule.every(5).minutes.do(self.job)
        self.stdout.write(self.style.WARNING(
            "📅 Agendado: 1 ciclo a cada 5 minutos\n"
            "   Inclui: Reddit + RSS\n"
            "   Pressione Ctrl+C para parar\n"
        ))
        
        # Executa primeiro ciclo imediatamente
        self.stdout.write(self.style.SUCCESS("🚀 Executando primeiro ciclo..."))
        self.job()
        
        # Loop principal
        while self.running:
            schedule.run_pending()
            time.sleep(1)