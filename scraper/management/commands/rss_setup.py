from django.core.management.base import BaseCommand
from scraper.models import RSSSource

class Command(BaseCommand):
    help = "Configura fontes RSS de notícias"

    def handle(self, *args, **kwargs):
        # Fontes RSS populares de notícias
        rss_sources = [
            {
                'name': 'G1 - Últimas Notícias',
                'url': 'https://g1.globo.com/rss/g1/',
            },
            {
                'name': 'BBC News - Brasil',
                'url': 'https://feeds.bbci.co.uk/portuguese/rss.xml',
            },
            {
                'name': 'UOL Notícias',
                'url': 'https://rss.uol.com.br/feed/noticias.xml',
            },
            {
                'name': 'Folha de S.Paulo',
                'url': 'https://feeds.folha.uol.com.br/emcimadahora/rss091.xml',
            },
            {
                'name': 'BBC News - World',
                'url': 'https://feeds.bbci.co.uk/news/world/rss.xml',
            },
            {
                'name': 'CNN Brasil',
                'url': 'https://www.cnnbrasil.com.br/feed/',
            },
            {
                'name': 'Reuters - Top News',
                'url': 'https://www.reutersagency.com/feed/',
            },
            {
                'name': 'TechCrunch',
                'url': 'https://techcrunch.com/feed/',
            },
        ]
        
        created = 0
        for source_data in rss_sources:
            source, is_new = RSSSource.objects.get_or_create(
                url=source_data['url'],
                defaults=source_data
            )
            if is_new:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"✅ {source_data['name']}"))
            else:
                self.stdout.write(f"⏭️ Já existe: {source_data['name']}")
        
        self.stdout.write(self.style.SUCCESS(f"\n📡 {created} novas fontes RSS configuradas!"))