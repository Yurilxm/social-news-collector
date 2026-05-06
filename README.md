# 🚀 Social News Collector - Módulo de Raspagem

Sistema de raspagem de dados para monitoramento de notícias em tempo real.  
Este módulo standalone foi integrado ao backend Django do projeto **IRIS** da **InterTV**.

---

## 📋 Funcionalidades

| Funcionalidade | Status |
|---------------|--------|
| Coleta automática do **Reddit** (subreddits e perfis) | ✅ |
| Coleta de feeds **RSS** (12 fontes: G1, BBC, UOL, CNN, etc.) | ✅ |
| Estrutura pronta para **X/Twitter** (API oficial) | 🐦 |
| Scheduler automático a cada 5 minutos | ⏱️ |
| Filtros de qualidade (4 camadas) | 🎯 |
| Detecção automática de região/cidade (Região dos Lagos - 7 cidades) | 🏙️ |
| Download de imagens dos artigos | 🖼️ |
| Persistência em TinyDB (JSON) | 💾 |
| Sistema anti-duplicata | 🔒 |

---

## 🛠️ Tecnologias

- **Python 3.11+**
- **TinyDB** (banco JSON leve)
- **Requests** (HTTP)
- **Feedparser** (RSS)
- **BeautifulSoup4 + lxml** (extração de artigos)
- **Tweepy** (Twitter/X - estruturado)
- **Schedule** (agendador)

---

## 📁 Estrutura do Projeto

    social-news-collector/
    ├── main.py                         # Entrada principal (CLI)
    ├── scraper/services/
    │   ├── reddit_collector.py         # Coleta Reddit com filtros
    │   ├── rss_collector.py            # Coleta RSS + download imagens
    │   ├── tinydb_service.py           # Banco JSON + filtros regionais
    │   └── twitter_collector.py        # Twitter/X (estrutura pronta)
    ├── config/
    │   └── bot_config.json             # Configuração de monitores
    ├── db/                             # Banco TinyDB (gerado automaticamente)
    ├── logs/                           # Logs de execução
    ├── requirements.txt
    └── README.md

---

## 🚦 Como Usar

### 1. Instalar dependências

    pip install -r requirements.txt

### 2. Configurar fontes

Edite `config/bot_config.json` com seus monitores e fontes RSS.

### 3. Executar coleta manual

    python main.py run-once

### 4. Iniciar scheduler automático

    python main.py run-loop

### 5. Visualizar notícias

    python main.py view-news --limit 10
    python main.py view-news --source rss --limit 5
    python main.py view-news --term "política"

### 6. Limpar banco

    python main.py clear-data

---

## 📊 Fontes Monitoradas

| Fonte | Tipo | Monitores |
|------|------|-----------|
| Reddit | API JSON pública | 4 (r/brasil, r/worldnews, r/news, r/technology) |
| RSS | Feeds públicos | 12 (G1, BBC, UOL, Folha, CNN, TechCrunch, The Verge, Wired, Google News) |
| X/Twitter | API Oficial | Estrutura pronta |

---

## 🎯 Sistema de Filtros (4 camadas)

- Tamanho mínimo: título + 300 caracteres ou 4 linhas  
- Anti-lixo: remove só links, CAPS excessivo, frases únicas  
- Parece notícia: verifica verbos jornalísticos e estrutura de manchete  
- Relevância: palavras-chave no título (+3pts) e conteúdo (+1pt)  

---

## 🏙️ Região dos Lagos

Detecção automática de 7 cidades:  
Cabo Frio, Búzios, Arraial do Cabo, Araruama, Saquarema, São Pedro da Aldeia, Iguaba Grande.

---

## 🐦 Ativando o Twitter/X

Crie um arquivo `.env`:

    TWITTER_BEARER_TOKEN=seu_token_aqui

---

## 💡 Nota sobre Django

Este módulo é standalone (não usa Django).  
A versão original usava Django ORM, mas foi simplificado para facilitar a integração.  
No projeto IRIS, este módulo foi integrado ao backend Django existente no servidor.

---

## 👤 Autor

Desenvolvido por Yuri Yam como parte do projeto IRIS - InterTV

📅 Maio 2026