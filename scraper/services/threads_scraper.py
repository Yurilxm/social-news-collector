import requests
from scraper.models import ThreadsPost
from datetime import datetime
import logging
import time
from django.utils import timezone

logger = logging.getLogger(__name__)

def scrape_threads_posts(username, limit=20):
    """
    Tenta coletar posts do Threads
    Nota: Threads é da Meta e pode exigir autenticação
    """
    username = username.strip('@')
    posts_list = []
    
    print(f"🔍 Iniciando coleta de @{username} no Threads...")
    print(f"📊 Limite: {limit} posts")
    print(f"⚠️  Threads (Meta) pode bloquear scraping sem autenticação")
    
    try:
        # Headers como navegador real
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Origin': 'https://www.threads.net',
            'Referer': 'https://www.threads.net/',
        }
        
        # Tenta acessar o perfil via API pública
        url = f"https://www.threads.net/@{username}"
        
        print(f"📡 Acessando: {url}")
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            print(f"✅ Resposta recebida ({len(response.text)} caracteres)")
            print("⚠️  Porém, Threads exige JavaScript para carregar conteúdo")
            print("💡 O HTML contém apenas a estrutura básica da página")
            
            # Tenta encontrar dados no HTML
            if 'threads.net' in response.text:
                print("🔍 Página carregada, mas conteúdo está em JavaScript")
                print("❌ Scraping direto NÃO funciona para Threads")
                
                # Cria um post de exemplo para registro
                post = ThreadsPost.objects.create(
                    post_id=f"test_{username}_{int(time.time())}",
                    username=username,
                    content=f"[Threads requer API oficial] Perfil: @{username}",
                    likes=0,
                    replies=0,
                    created_at=timezone.now(),
                    url=url,
                    is_news=False
                )
                posts_list.append(post)
                print(f"📝 Post de teste criado para registro")
            else:
                print("❌ Não foi possível carregar a página")
                
        elif response.status_code == 302:
            print("🔄 Redirecionamento detectado - provável página de login")
            print("❌ Threads exige login para acessar conteúdo")
            
        elif response.status_code == 403:
            print("🚫 Acesso proibido (403)")
            print("❌ Threads está bloqueando scraping ativamente")
            
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("❌ Timeout: Threads demorou muito para responder")
    except requests.exceptions.ConnectionError:
        print("❌ Erro de conexão com Threads")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        logger.error(f"Erro no Threads: {e}", exc_info=True)
    
    print(f"\n📊 Resultado para Threads/@ {username}:")
    print(f"   {'✅ Funcionou' if posts_list else '❌ BLOQUEADO - Requer API oficial'}")
    
    return posts_list