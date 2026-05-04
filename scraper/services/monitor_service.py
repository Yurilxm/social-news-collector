import requests
from scraper.models import RedditPost, RedditComment, MonitorConfig, FilteredPost
from datetime import datetime, timezone as dt_timezone, timedelta
import logging
import time
from django.utils import timezone
from django.db.models import Q

logger = logging.getLogger(__name__)

class RedditMonitor:
    """Sistema de monitoramento automático do Reddit - Versão 2.0"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'SocialNewsMonitor/2.0',
            'Accept': 'application/json',
        }
        self.stats = {
            'posts_collected': 0,
            'posts_filtered': 0,
            'comments_collected': 0,
            'errors': 0,
        }
    
    def collect_posts(self, target, monitor_type='subreddit', limit=50, start_date=None):
        """
        Coleta posts de subreddit ou usuário
        
        Args:
            target: Nome do subreddit (r/brasil) ou usuário (u/username)
            monitor_type: 'subreddit' ou 'user'
            limit: Máximo de posts
            start_date: Data inicial (datetime) - só coleta posts após esta data
        """
        if monitor_type == 'subreddit':
            url = f"https://www.reddit.com/r/{target}/new.json"
        else:
            url = f"https://www.reddit.com/user/{target}/submitted.json"
        
        params = {'limit': limit}
        posts = []
        
        try:
            print(f"   📡 Acessando: {url.split('?')[0]}")
            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            
            if response.status_code == 404:
                print(f"   ⚠️ {target} não encontrado (404)")
                return []
            
            if response.status_code != 200:
                print(f"   ❌ Erro HTTP: {response.status_code}")
                return []
            
            data = response.json()
            children = data.get('data', {}).get('children', [])
            
            if not children:
                print(f"   📭 Nenhum post encontrado")
                return []
            
            filtered_by_date = 0
            
            for item in children:
                post = item['data']
                
                # Pula posts fixados
                if post.get('stickied', False):
                    continue
                
                # Converte data do post
                post_date = datetime.fromtimestamp(
                    post['created_utc'], 
                    tz=dt_timezone.utc
                )
                
                # Filtro por data inicial
                if start_date and post_date < start_date:
                    filtered_by_date += 1
                    continue
                
                # Salva ou atualiza
                reddit_post, created = RedditPost.objects.update_or_create(
                    reddit_id=post['id'],
                    defaults={
                        'title': post['title'],
                        'content': post.get('selftext', '')[:2000],
                        'author': post.get('author', '[deleted]'),
                        'subreddit': post.get('subreddit', target),
                        'url': f"https://reddit.com{post['permalink']}",
                        'score': post.get('score', 0),
                        'num_comments': post.get('num_comments', 0),
                        'created_utc': post_date,
                    }
                )
                
                if created:
                    posts.append(reddit_post)
                    self.stats['posts_collected'] += 1
                    score_emoji = '🔥' if post.get('score', 0) > 1000 else '📊'
                    print(f"   {score_emoji} Novo: {post['title'][:70]}...")
                
                time.sleep(0.15)  # Rate limit mais agressivo para teste
            
            if filtered_by_date > 0:
                print(f"   ⏪ {filtered_by_date} posts ignorados (antes da data inicial)")
            
            return posts
            
        except Exception as e:
            logger.error(f"Erro ao coletar {target}: {e}")
            self.stats['errors'] += 1
            return []
    
    def collect_comments(self, post, keywords=None, limit=10):
        """Coleta comentários de um post específico"""
        if post.num_comments == 0:
            return []
        
        # Extrai o path do post da URL
        post_path = post.url.replace('https://reddit.com', '')
        url = f"https://www.reddit.com{post_path}.json"
        params = {'limit': limit, 'depth': 1}
        
        comments_list = []
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            
            # Reddit retorna [post_data, comments_data]
            if len(data) < 2:
                return []
            
            comments_data = data[1]['data']['children']
            
            for item in comments_data:
                if item['kind'] != 't1':  # t1 = comment
                    continue
                
                comment = item['data']
                comment_text = comment.get('body', '')
                
                # Filtra por keywords se necessário
                if keywords:
                    has_match = any(
                        kw.lower() in comment_text.lower() 
                        for kw in keywords
                    )
                    if not has_match:
                        continue
                
                comment_id = comment['id']
                comment_date = datetime.fromtimestamp(
                    comment['created_utc'],
                    tz=dt_timezone.utc
                )
                
                # Salva comentário
                reddit_comment, created = RedditComment.objects.update_or_create(
                    comment_id=comment_id,
                    defaults={
                        'post': post,
                        'author': comment.get('author', '[deleted]'),
                        'content': comment_text[:1000],
                        'score': comment.get('score', 0),
                        'created_utc': comment_date,
                        'matched_keywords': ', '.join(keywords) if keywords else '',
                    }
                )
                
                if created:
                    comments_list.append(reddit_comment)
                    self.stats['comments_collected'] += 1
                    
                    if comment.get('score', 0) > 10:
                        print(f"      💬 Comentário relevante (+{comment['score']}): {comment_text[:60]}...")
            
        except Exception as e:
            logger.error(f"Erro ao coletar comentários: {e}")
        
        time.sleep(0.1)
        return comments_list
    
    def filter_by_keywords(self, post, keywords):
        """Filtra post por palavras-chave com pontuação de relevância"""
        if not keywords:
            return True, [], 1.0
        
        keyword_list = [k.strip().lower() for k in keywords.split(',') if k.strip()]
        title_lower = post.title.lower()
        content_lower = post.content.lower()
        
        matched = []
        score = 0.0
        
        for keyword in keyword_list:
            # Pontuação maior para match no título
            if keyword in title_lower:
                matched.append(keyword)
                score += 2.0
            
            # Pontuação menor para match no conteúdo
            if keyword in content_lower:
                if keyword not in matched:
                    matched.append(keyword)
                score += 1.0
        
        # Bônus por múltiplos matches
        if len(matched) >= 3:
            score *= 1.5
        
        return len(matched) > 0, matched, score
    
    def run_monitor(self, monitor_config):
        """Executa um monitor específico"""
        type_label = 'r/' if monitor_config.monitor_type == 'subreddit' else 'u/'
        
        print(f"\n{'='*60}")
        print(f"🔍 [{timezone.now().strftime('%H:%M:%S')}] {monitor_config.name}")
        print(f"   Alvo: {type_label}{monitor_config.target}")
        print(f"   Tipo: {monitor_config.get_monitor_type_display()}")
        print(f"   Palavras-chave: {monitor_config.keywords or 'Todas'}")
        print(f"   Score mínimo: {monitor_config.min_score}")
        print(f"   Data inicial: {monitor_config.start_date or 'Sem filtro'}")
        print(f"   Comentários: {'Sim' if monitor_config.collect_comments else 'Não'}")
        print(f"{'='*60}")
        
        # Coleta novos posts
        new_posts = self.collect_posts(
            target=monitor_config.target,
            monitor_type=monitor_config.monitor_type,
            limit=30,
            start_date=monitor_config.start_date
        )
        
        print(f"   📥 Posts novos: {len(new_posts)}")
        
        # Filtra por keywords e score
        filtered_count = 0
        for post in new_posts:
            # Verifica score mínimo
            if post.score < monitor_config.min_score:
                continue
            
            # Filtra por keywords
            has_match, matched_keywords, relevance = self.filter_by_keywords(
                post, monitor_config.keywords
            )
            
            if has_match or not monitor_config.keywords:
                # Cria registro filtrado
                filtered_post, created = FilteredPost.objects.get_or_create(
                    reddit_post=post,
                    monitor=monitor_config,
                    defaults={
                        'matched_keywords': ', '.join(matched_keywords),
                        'relevance_score': relevance,
                        'is_sent': False,
                    }
                )
                
                if created:
                    filtered_count += 1
                    self.stats['posts_filtered'] += 1
                    print(f"   ✅ [Relevância: {relevance:.1f}] {post.title[:80]}")
                    if matched_keywords:
                        print(f"      🔑 {', '.join(matched_keywords)}")
                    
                    # Coleta comentários se configurado
                    if monitor_config.collect_comments and post.num_comments > 0:
                        keyword_list = [k.strip() for k in monitor_config.keywords.split(',')] if monitor_config.keywords else None
                        self.collect_comments(post, keywords=keyword_list, limit=5)
        
        # Atualiza último run e reseta start_date após primeira execução
        monitor_config.last_run = timezone.now()
        if monitor_config.start_date:
            monitor_config.start_date = None  # Remove filtro após primeira coleta histórica
        monitor_config.save()
        
        print(f"   📊 Posts relevantes: {filtered_count}")
        return filtered_count
    
    def run_all_active_monitors(self):
        """Executa todos os monitores ativos"""
        active_monitors = MonitorConfig.objects.filter(is_active=True)
        
        if not active_monitors:
            print("⚠️ Nenhum monitor configurado!")
            return 0
        
        # Reset stats
        self.stats = {
            'posts_collected': 0,
            'posts_filtered': 0,
            'comments_collected': 0,
            'errors': 0,
        }
        
        print(f"\n{'='*60}")
        print(f"🚀 CICLO DE MONITORAMENTO")
        print(f"📡 {active_monitors.count()} monitores ativos")
        print(f"🕐 {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"{'='*60}")
        
        total_posts = 0
        for monitor in active_monitors:
            posts = self.run_monitor(monitor)
            total_posts += posts
            time.sleep(1)  # Pausa entre monitores (reduzida para teste)
        
        print(f"\n{'='*60}")
        print(f"📊 RESUMO DO CICLO")
        print(f"{'='*60}")
        print(f"   📥 Posts coletados: {self.stats['posts_collected']}")
        print(f"   ✅ Posts filtrados: {self.stats['posts_filtered']}")
        print(f"   💬 Comentários: {self.stats['comments_collected']}")
        print(f"   ❌ Erros: {self.stats['errors']}")
        print(f"   🕐 Próximo ciclo: {(timezone.now() + timedelta(minutes=5)).strftime('%H:%M:%S')}")
        print(f"{'='*60}\n")
        
        return total_posts