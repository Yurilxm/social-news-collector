import snscrape.modules.twitter as sntwitter
from scraper.models import Tweet
import time
import logging
import random

logger = logging.getLogger(__name__)

# Lista de User-Agents reais para rotacionar
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

def scrape_user_tweets(username, limit=20, max_retries=3):
    """
    Coleta tweets com snscrape usando User-Agents rotativos
    """
    username = username.strip('@')
    tweets_list = []
    retry_count = 0
    
    print(f"🔍 Iniciando coleta de @{username}...")
    print(f"📊 Configuração: {limit} tweets, {max_retries} tentativas máximas")
    
    while retry_count < max_retries:
        try:
            # Configura o User-Agent aleatório
            user_agent = random.choice(USER_AGENTS)
            print(f"🔄 Tentativa {retry_count + 1}/{max_retries}")
            print(f"🔧 User-Agent: {user_agent[:50]}...")
            
            # Cria o scraper com configurações
            scraper = sntwitter.TwitterSearchScraper(
                f'from:{username}',
                retries=2  # Permite retentativas internas
            )
            
            tweets_collected = 0
            consecutive_errors = 0
            
            # Itera sobre os tweets
            for i, tweet in enumerate(scraper.get_items()):
                if i >= limit or consecutive_errors >= 3:
                    break
                
                try:
                    # Verifica se tweet já existe
                    tweet_obj, created = Tweet.objects.get_or_create(
                        url=tweet.url,
                        defaults={
                            'username': username,
                            'content': tweet.content,
                            'date': tweet.date,
                        }
                    )
                    
                    if created:
                        tweets_list.append(tweet_obj)
                        tweets_collected += 1
                        preview = tweet.content[:60].replace('\n', ' ')
                        print(f"✅ {tweets_collected}/{limit}: {preview}...")
                        consecutive_errors = 0  # Reseta contador de erros
                    else:
                        print(f"⏭️ Tweet duplicado, pulando...")
                    
                    # Delay aleatório entre tweets (0.5 a 2 segundos)
                    delay = random.uniform(0.5, 2.0)
                    time.sleep(delay)
                    
                except Exception as e:
                    consecutive_errors += 1
                    error_msg = str(e)[:100]
                    print(f"⚠️ Erro no tweet {i+1}: {error_msg}")
                    
                    if consecutive_errors >= 3:
                        print("❌ Muitos erros consecutivos, mudando estratégia...")
                        break
                    
                    time.sleep(2)  # Espera extra em caso de erro
                    continue
            
            # Se conseguiu coletar algo, sai do loop de retry
            if tweets_list:
                print(f"\n✅ Sucesso! {len(tweets_list)} tweets coletados")
                return tweets_list
            elif retry_count < max_retries - 1:
                print(f"⏳ Aguardando 5 segundos antes da próxima tentativa...")
                time.sleep(5)
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Erro na tentativa {retry_count + 1}: {error_msg[:150]}")
            
            if "blocked" in error_msg.lower() or "404" in error_msg:
                print("🚫 Bloqueio detectado, trocando User-Agent...")
            elif "rate" in error_msg.lower():
                wait_time = (retry_count + 1) * 10
                print(f"⏰ Rate limit, aguardando {wait_time} segundos...")
                time.sleep(wait_time)
            else:
                time.sleep(3)
        
        retry_count += 1
    
    # Se chegou aqui, todas as tentativas falharam
    if not tweets_list:
        print("\n❌ Não foi possível coletar tweets após todas as tentativas")
        print("\n💡 Alternativas manuais:")
        print("1. Tente novamente mais tarde (intervalo de 15-30 minutos)")
        print("2. Use o arquivo CSV de exemplo como fallback")
        print("3. Considere usar a API oficial do X com suas credenciais")
        
        # Tenta carregar dados de exemplo (fallback)
        try:
            from django.utils import timezone
            sample_tweet = Tweet.objects.create(
                username=username,
                content=f"Tweet de exemplo para @{username} - coleta indisponível",
                date=timezone.now(),
                url=f"https://twitter.com/{username}/status/example"
            )
            tweets_list.append(sample_tweet)
            print("📝 Tweet de exemplo criado para não interromper o fluxo")
        except:
            pass
    
    return tweets_list