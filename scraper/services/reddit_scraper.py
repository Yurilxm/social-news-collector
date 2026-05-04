import requests
from scraper.models import RedditPost
from datetime import datetime
import logging
import time
from django.utils import timezone

logger = logging.getLogger(__name__)

def scrape_reddit_posts(subreddit_name, limit=20):
    """
    Coleta posts do Reddit usando a API JSON pública
    NÃO requer autenticação - sempre funciona
    """
    subreddit_name = subreddit_name.strip('r/').strip('/')
    posts_list = []
    
    print(f"🔍 Iniciando coleta do r/{subreddit_name}...")
    print(f"📊 Limite: {limit} posts")
    print(f"ℹ️  Usando API JSON pública do Reddit")
    
    try:
        # Headers que simulam um navegador real
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        }
        
        # API JSON pública do Reddit (formato .json)
        url = f"https://www.reddit.com/r/{subreddit_name}/hot.json"
        params = {'limit': limit}
        
        print(f"📡 Acessando: reddit.com/r/{subreddit_name}/hot.json")
        
        # Faz a requisição
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        # Verifica se a requisição foi bem sucedida
        if response.status_code != 200:
            print(f"❌ Erro HTTP: {response.status_code}")
            if response.status_code == 429:
                print("⏰ Rate limit! Aguardando 10 segundos...")
                time.sleep(10)
            return []
        
        # Parse do JSON
        data = response.json()
        posts_data = data.get('data', {}).get('children', [])
        
        if not posts_data:
            print(f"⚠️ Nenhum post encontrado em r/{subreddit_name}")
            return []
        
        print(f"📥 {len(posts_data)} posts recebidos da API\n")
        
        # Processa cada post
        for i, item in enumerate(posts_data, 1):
            try:
                post = item['data']
                
                # Pula posts fixados (stickied)
                if post.get('stickied', False):
                    print(f"📌 {i}/{len(posts_data)}: Post fixado - pulando...")
                    continue
                
                # Verifica se já existe no banco
                if RedditPost.objects.filter(reddit_id=post['id']).exists():
                    print(f"⏭️ {i}/{len(posts_data)}: Já existe - {post['title'][:60]}...")
                    continue
                
                # Extrai informações
                title = post.get('title', 'Sem título')
                content = post.get('selftext', '')[:1000]
                author = post.get('author', '[deleted]')
                score = post.get('score', 0)
                num_comments = post.get('num_comments', 0)
                permalink = post.get('permalink', '')
                
                # ← REMOVIDA a importação duplicada daqui
                created_utc = timezone.make_aware(
                    datetime.fromtimestamp(post.get('created_utc', time.time())),
                    timezone=timezone.utc
                )
                
                # Cria o post no banco
                reddit_post = RedditPost.objects.create(
                    reddit_id=post['id'],
                    title=title,
                    content=content,
                    author=author,
                    subreddit=subreddit_name,
                    url=f"https://reddit.com{permalink}",
                    score=score,
                    num_comments=num_comments,
                    created_utc=created_utc,
                    is_news=False
                )
                
                posts_list.append(reddit_post)
                
                # Preview formatado
                title_preview = title[:80] + '...' if len(title) > 80 else title
                print(f"✅ {i}/{len(posts_data)}:")
                print(f"   📰 {title_preview}")
                print(f"   👍 {score} upvotes | 💬 {num_comments} comentários | ✍️ u/{author}")
                print()
                
                # Pequena pausa entre posts
                time.sleep(0.3)
                
            except Exception as e:
                print(f"⚠️ Erro no post {i}: {str(e)[:100]}")
                continue
        
        # Resumo final
        total_recebidos = len(posts_data)
        total_salvos = len(posts_list)
        
        print(f"\n{'='*50}")
        print(f"📊 RESUMO DA COLETA")
        print(f"{'='*50}")
        print(f"📥 Posts recebidos: {total_recebidos}")
        print(f"✅ Posts salvos: {total_salvos}")
        print(f"⏭️ Já existiam: {total_recebidos - total_salvos}")
        
        if posts_list:
            # Mostra o post mais votado
            top_post = max(posts_list, key=lambda x: x.score)
            print(f"\n🏆 Post mais votado:")
            print(f"   {top_post.title[:100]}")
            print(f"   👍 {top_post.score} upvotes")
        
    except requests.exceptions.Timeout:
        print("❌ Timeout: Reddit demorou muito para responder")
    except requests.exceptions.ConnectionError:
        print("❌ Erro de conexão: Verifique sua internet")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        logger.error(f"Erro no Reddit: {e}", exc_info=True)
    
    return posts_list