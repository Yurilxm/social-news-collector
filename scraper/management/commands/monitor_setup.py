from django.core.management.base import BaseCommand
from scraper.models import MonitorConfig
from datetime import datetime, timezone as dt_timezone, timedelta

class Command(BaseCommand):
    help = "Configura monitores pré-definidos para teste"

    def handle(self, *args, **kwargs):
        # Data inicial: ontem ao meio-dia (exemplo do chefe)
        start = datetime.now(dt_timezone.utc) - timedelta(days=1)
        start = start.replace(hour=12, minute=0, second=0, microsecond=0)
        
        default_monitors = [
            {
                'name': 'Notícias Brasil',
                'monitor_type': 'subreddit',
                'target': 'brasil',
                'keywords': 'política, governo, economia, brasil, STF, congresso',
                'min_score': 20,
                'interval_minutes': 5,
                'start_date': start,
                'collect_comments': True,
            },
            {
                'name': 'Notícias Mundo',
                'monitor_type': 'subreddit',
                'target': 'worldnews',
                'keywords': 'war, peace, election, crisis, deal, trade, UN, NATO',
                'min_score': 100,
                'interval_minutes': 5,
                'start_date': start,
                'collect_comments': False,
            },
            {
                'name': 'Tecnologia',
                'monitor_type': 'subreddit',
                'target': 'technology',
                'keywords': 'AI, artificial intelligence, robot, startup, innovation',
                'min_score': 50,
                'interval_minutes': 5,
                'start_date': start,
                'collect_comments': False,
            },
            {
                'name': 'Perfil BBC News',
                'monitor_type': 'user',
                'target': 'BBCNews',
                'keywords': 'breaking, exclusive, report, update',
                'min_score': 50,
                'interval_minutes': 5,
                'start_date': start,
                'collect_comments': True,
            },
            {
                'name': 'Perfil Reuters',
                'monitor_type': 'user',
                'target': 'Reuters',
                'keywords': 'breaking, exclusive, report, update',
                'min_score': 50,
                'interval_minutes': 5,
                'start_date': start,
                'collect_comments': True,
            },
        ]
        
        created = 0
        for config in default_monitors:
            monitor, is_new = MonitorConfig.objects.get_or_create(
                name=config['name'],
                defaults=config
            )
            if is_new:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Criado: {config['name']}"))
            else:
                # Atualiza config existente
                for key, value in config.items():
                    setattr(monitor, key, value)
                monitor.save()
                self.stdout.write(f"🔄 Atualizado: {config['name']}")
        
        self.stdout.write(self.style.SUCCESS(
            f"\n🎯 {created} monitores configurados!"
        ))
        self.stdout.write(f"📅 Data inicial: {start.strftime('%d/%m/%Y %H:%M')}")
        self.stdout.write(f"⏱️  Intervalo: 5 minutos")