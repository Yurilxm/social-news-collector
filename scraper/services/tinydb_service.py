"""
Serviço TinyDB para salvar dados da raspagem
Banco leve em JSON - Preparado para parseamento futuro por LLM
Suporta tanto TinyDB quanto PostgreSQL (via Django ORM)
"""

import os
from datetime import datetime
from tinydb import TinyDB, Query
import logging

logger = logging.getLogger(__name__)

# Caminho do banco TinyDB
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'db')

# Cidades da Região dos Lagos
CIDADES_REGIAO_LAGOS = [
    'cabo frio', 'búzios', 'buzios', 'arraial do cabo', 'arraial',
    'araruama', 'saquarema', 'são pedro da aldeia', 'iguaba grande'
]

KEYWORDS_POR_CIDADE = {
    'cabo_frio': ['cabo frio', 'cabofrio', 'praia do forte', 'peró'],
    'buzios': ['búzios', 'buzios', 'rua das pedras', 'geribá'],
    'arraial_do_cabo': ['arraial do cabo', 'arraial', 'pontal', 'prainha'],
    'araruama': ['araruama', 'lagoa de araruama'],
    'saquarema': ['saquarema', 'itaúna', 'vila', 'bacaxá'],
    'sao_pedro_da_aldeia': ['são pedro da aldeia', 'são pedro'],
    'iguaba_grande': ['iguaba grande', 'iguaba'],
}


class TinyDBService:
    """Gerencia o banco TinyDB para dados de raspagem"""
    
    def __init__(self):
        os.makedirs(DB_PATH, exist_ok=True)
        
        self.db_noticias = TinyDB(os.path.join(DB_PATH, 'noticias.json'))
        self.db_reddit = TinyDB(os.path.join(DB_PATH, 'reddit.json'))
        self.db_rss = TinyDB(os.path.join(DB_PATH, 'rss.json'))
        self.db_logs = TinyDB(os.path.join(DB_PATH, 'logs.json'))
        
        self.stats = {
            'salvos': 0,
            'duplicados': 0,
            'erros': 0,
        }
    
    def detectar_regiao(self, texto, keywords_monitor=None):
        """Detecta a região/cidade baseado no conteúdo do texto"""
        texto_lower = texto.lower()
        
        for cidade_key, keywords in KEYWORDS_POR_CIDADE.items():
            for kw in keywords:
                if kw in texto_lower:
                    return {
                        'regiao': 'Região dos Lagos',
                        'cidade': cidade_key.replace('_', ' ').title(),
                        'match': kw
                    }
        
        if keywords_monitor:
            for kw in keywords_monitor:
                if kw.lower() in texto_lower:
                    for cidade_key, cidade_kws in KEYWORDS_POR_CIDADE.items():
                        if kw.lower() in cidade_kws:
                            return {
                                'regiao': 'Região dos Lagos',
                                'cidade': cidade_key.replace('_', ' ').title(),
                                'match': kw
                            }
        
        return {'regiao': 'Nacional', 'cidade': None, 'match': None}
    
    def salvar_noticia(self, dados):
        """Salva uma notícia no banco unificado"""
        try:
            Noticia = Query()
            existente = self.db_noticias.search(Noticia.id == dados['id'])
            
            if existente:
                self.stats['duplicados'] += 1
                return None
            
            texto_busca = f"{dados.get('titulo', '')} {dados.get('conteudo', '')}"
            regiao_info = self.detectar_regiao(texto_busca, dados.get('palavras_chave', []))
            
            documento = {
                'id': dados['id'],
                'titulo': dados.get('titulo', ''),
                'conteudo': dados.get('conteudo', '')[:2000],
                'fonte': dados.get('fonte', 'desconhecida'),
                'url': dados.get('url', ''),
                'autor': dados.get('autor', ''),
                'data_publicacao': dados.get('data_publicacao', datetime.now().isoformat()),
                'data_coleta': datetime.now().isoformat(),
                'score': dados.get('score', 0),
                'comentarios': dados.get('comentarios', 0),
                'palavras_chave': dados.get('palavras_chave', []),
                'relevancia': dados.get('relevancia', 0),
                'regiao': regiao_info['regiao'],
                'cidade': regiao_info['cidade'],
                'match_regiao': regiao_info['match'],
                'subreddit': dados.get('subreddit', ''),
                'feed_name': dados.get('feed_name', ''),
                'is_fake_news': None,
                'importance_level': 0,
                'sentimento': None,
            }
            
            self.db_noticias.insert(documento)
            
            if dados.get('fonte') == 'reddit':
                self.db_reddit.insert(documento)
            elif dados.get('fonte') == 'rss':
                self.db_rss.insert(documento)
            
            self.stats['salvos'] += 1
            return documento
            
        except Exception as e:
            logger.error(f"Erro ao salvar no TinyDB: {e}")
            self.stats['erros'] += 1
            return None
    
    def buscar_por_regiao(self, regiao, limite=50):
        Noticia = Query()
        return self.db_noticias.search(Noticia.regiao == regiao)[:limite]
    
    def buscar_por_cidade(self, cidade, limite=50):
        Noticia = Query()
        return self.db_noticias.search(Noticia.cidade == cidade)[:limite]
    
    def get_stats(self):
        return {
            'total_noticias': len(self.db_noticias),
            'total_reddit': len(self.db_reddit),
            'total_rss': len(self.db_rss),
            'por_regiao': self.contar_por_regiao(),
            'por_cidade': self.contar_por_cidade(),
        }
    
    def contar_por_regiao(self):
        contagem = {}
        for n in self.db_noticias.all():
            regiao = n.get('regiao', 'Desconhecida')
            contagem[regiao] = contagem.get(regiao, 0) + 1
        return contagem
    
    def contar_por_cidade(self):
        contagem = {}
        for n in self.db_noticias.all():
            cidade = n.get('cidade')
            if cidade:
                contagem[cidade] = contagem.get(cidade, 0) + 1
        return contagem
    
    def registrar_log(self, mensagem, tipo='info', dados=None):
        self.db_logs.insert({
            'timestamp': datetime.now().isoformat(),
            'tipo': tipo,
            'mensagem': mensagem,
            'dados': dados or {}
        })