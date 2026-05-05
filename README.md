# 🚀 Social News Collector - Base do Projeto IRIS

Sistema de raspagem de dados para monitoramento de notícias em tempo real,  
desenvolvido como base para o projeto **IRIS** da **InterTV**.

---

## 📋 Funcionalidades

| Funcionalidade | Status |
|---------------|--------|
| Coleta automática do **Reddit** (subreddits e perfis) | ✅ |
| Coleta de feeds **RSS** (G1, BBC, UOL, CNN, Folha, TechCrunch) | ✅ |
| Estrutura pronta para **X/Twitter** (API oficial) | 🐦 |
| Scheduler automático a cada 5 minutos | ⏱️ |
| Filtro por palavras-chave com pontuação de relevância | 🎯 |
| Detecção automática de região/cidade (Região dos Lagos) | 🏙️ |
| Persistência em TinyDB (JSON) e Django ORM (PostgreSQL) | 💾 |
| Integração com Docker | 🐳 |
| Sistema anti-duplicata | 🔒 |

---

## 🛠️ Tecnologias

- **Python 3.11**
- **Django 5.2** (ORM + gestão de comandos)
- **TinyDB 4.8** (banco JSON leve)
- **PostgreSQL** (produção)
- **Requests** (HTTP)
- **Feedparser** (RSS)
- **Schedule** (agendador)
- **Tweepy** (Twitter/X - estruturado)
- **Docker** (containerização)

---

## 📁 Estrutura do Projeto

social-news-collector/
├── scraper/
│   ├── services/
│   │   ├── monitor_service.py      # Coleta Reddit (API JSON pública)
│   │   ├── rss_service.py          # Coleta RSS (feeds públicos)
│   │   ├── tinydb_service.py       # Banco JSON com filtros regionais
│   │   └── twitter_service.py      # Twitter/X (API oficial - estruturado)
│   ├── models.py                  # Modelos Django (PostgreSQL)
│   └── management/commands/
│       ├── monitor_setup.py       # Configurar monitores
│       ├── rss_setup.py           # Configurar fontes RSS
│       ├── monitor_run.py         # Executar 1 ciclo manual
│       ├── monitor_scheduler.py   # Scheduler automático
│       └── monitor_report.py      # Relatórios
├── requirements.txt
└── README.md

---

## 🚦 Como Usar

### 1. Instalar dependências
pip install -r requirements.txt

### 2. Configurar fontes de dados
python manage.py monitor_setup  
python manage.py rss_setup

### 3. Executar coleta manual (1 ciclo)
python manage.py monitor_run

### 4. Iniciar scheduler automático (a cada 5 min)
python manage.py monitor_scheduler

### 5. Ver relatório
python manage.py monitor_report --hours 24

---

## 📊 Fontes Monitoradas

| Fonte       | Tipo               | Monitores                                                                 | Status |
|------------|--------------------|---------------------------------------------------------------------------|--------|
| Reddit     | API JSON pública   | r/brasil, r/worldnews, r/technology, u/BBCNews, u/Reuters                | ✅ |
| RSS        | Feeds públicos     | G1, BBC Brasil, UOL, Folha, BBC World, CNN Brasil, TechCrunch           | ✅ |
| X/Twitter  | API Oficial        | Estrutura pronta                                                        | ⏸️ |

---

## 🎯 Sistema de Filtros

### Por Palavras-chave
Cada monitor tem keywords específicas. O sistema pontua:

- Match no título = **2x**
- Match no conteúdo = **1x**
- 3+ matches = **bônus 1.5x**

### Por Região/Cidade
Detecção automática de cidades da Região dos Lagos:

Cabo Frio, Búzios, Arraial do Cabo, Araruama, Saquarema, São Pedro da Aldeia, Iguaba Grande

### Por Relevância
Score mínimo configurável por monitor (ex: 20 no Brasil, 100 no Mundo)

---

## 💾 Bancos de Dados

| Banco        | Uso                     | Arquivo             |
|-------------|--------------------------|---------------------|
| TinyDB      | Desenvolvimento/Testes   | db/noticias.json    |
| PostgreSQL  | Produção (servidor)      | Tabelas Django      |

O TinyDB foi escolhido como ponte para o banco futuro de parseamento por LLM,  
pois seu formato JSON é compatível com o pipeline de IA planejado.

---

## 🐦 Ativando o Twitter/X

1. Crie uma conta de desenvolvedor em: https://developer.twitter.com  
2. Obtenha o Bearer Token no plano Free  
3. Crie um arquivo `.env`:

TWITTER_BEARER_TOKEN=seu_token_aqui

O scheduler já está integrado — o Twitter será coletado automaticamente!

---

## 🔮 Próximos Passos

- Ativar API do Twitter/X  
- Criar API REST para frontend React  
- Integrar pop-ups de notificação (por tipo de usuário)  
- Integrar Instagram/Facebook via API Graph (Meta)  
- Implementar verificação de fake news com IA  
- Classificação automática por categorias  

---

## 👤 Autor

Desenvolvido por Yuri Lima como parte do projeto IRIS - InterTV  

📅 Maio 2026