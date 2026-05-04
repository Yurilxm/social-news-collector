import feedparser
from scraper.models import RSSSource, RSSEntry
from datetime import datetime, timezone as dt_timezone
from django.utils import timezone
import logging
import time

logger = logging.getLogger(__name__)

class RSSMonitor:
    """Coletor de feeds RSS"""
    
    def __init__(self):
        self.stats = {
            'feeds_checked': 0,
            'entries_collected': 0,
            'errors': 0,
        }
    
    def fetch_feed(self, rss_source):
        """Coleta entradas de um feed RSS"""
        print(f"\n📡 [{rss_source.name}]")
        print(f"   URL: {rss_source.url}")
        
        try:
            # Parse do feed
            feed = feedparser.parse(rss_source.url)
            
            if feed.bozo:  # Erro no parse
                print(f"   ⚠️ Aviso: {str(feed.bozo_exception)[:100]}")
            
            # Verifica se tem entradas
            if not feed.entries:
                print(f"   📭 Nenhuma entrada encontrada")
                rss_source.last_fetch = timezone.now()
                rss_source.save()
                self.stats['feeds_checked'] += 1
                return 0
            
            entries_saved = 0
            print(f"   📥 {len(feed.entries)} entradas no feed")
            
            for entry in feed.entries[:30]:  # Limite de 30 por coleta
                try:
                    # Gera ID único
                    entry_id = entry.get('id', entry.get('link', ''))
                    if not entry_id:
                        continue
                    
                    # Extrai data
                    published = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published = datetime.fromtimestamp(
                            time.mktime(entry.published_parsed),
                            tz=dt_timezone.utc
                        )
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        published = datetime.fromtimestamp(
                            time.mktime(entry.updated_parsed),
                            tz=dt_timezone.utc
                        )
                    else:
                        published = timezone.now()
                    
                    # Extrai conteúdo
                    content = ''
                    if hasattr(entry, 'content'):
                        content = entry.content[0].get('value', '')
                    elif hasattr(entry, 'summary'):
                        content = entry.summary
                    elif hasattr(entry, 'description'):
                        content = entry.description
                    
                    # Remove tags HTML do conteúdo
                    import re
                    content = re.sub(r'<[^>]+>', '', content)[:2000]
                    
                    # Salva entrada
                    rss_entry, created = RSSEntry.objects.update_or_create(
                        entry_id=entry_id[:500],
                        defaults={
                            'source': rss_source,
                            'title': entry.get('title', 'Sem título')[:500],
                            'content': content,
                            'author': entry.get('author', '')[:255],
                            'url': entry.get('link', ''),
                            'published_at': published,
                        }
                    )
                    
                    if created:
                        entries_saved += 1
                        self.stats['entries_collected'] += 1
                        print(f"   ✅ {entry.get('title', '')[:70]}...")
                    
                except Exception as e:
                    logger.error(f"Erro ao processar entrada: {e}")
                    continue
            
            # Atualiza última coleta
            rss_source.last_fetch = timezone.now()
            rss_source.save()
            
            self.stats['feeds_checked'] += 1
            print(f"   📊 {entries_saved} novas entradas")
            return entries_saved  # ← Agora sempre retorna int
            
        except Exception as e:
            logger.error(f"Erro no feed {rss_source.name}: {e}")
            self.stats['errors'] += 1
            print(f"   ❌ Erro: {str(e)[:100]}")
            return 0  # ← Retorna 0 em caso de erro
    
    def run_all_feeds(self):
        """Executa coleta em todas as fontes ativas"""
        sources = RSSSource.objects.filter(is_active=True)
        
        if not sources.exists():
            print("⚠️ Nenhuma fonte RSS configurada!")
            return 0
        
        # Reset stats
        self.stats = {
            'feeds_checked': 0,
            'entries_collected': 0,
            'errors': 0,
        }
        
        print(f"\n{'='*60}")
        print(f"📡 COLETA RSS")
        print(f"📋 {sources.count()} fontes ativas")
        print(f"🕐 {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"{'='*60}")
        
        total_entries = 0
        for source in sources:
            entries = self.fetch_feed(source)
            total_entries += entries
            time.sleep(0.5)  # Respeitar servidores
        
        print(f"\n{'='*60}")
        print(f"📊 RESUMO RSS")
        print(f"{'='*60}")
        print(f"   📡 Feeds verificados: {self.stats['feeds_checked']}")
        print(f"   ✅ Entradas novas: {self.stats['entries_collected']}")
        print(f"   ❌ Erros: {self.stats['errors']}")
        print(f"{'='*60}\n")
        
        return total_entries