# Social News Collector

Sistema de coleta automatizada de dados de redes sociais e portais de notícias.

## 🚀 Tecnologias
- Python
- Django
- SQLite
- RSS Feeds
- Reddit Scraper

## 📊 Funcionalidades
- Coleta de notícias via RSS
- Coleta de posts do Reddit
- Armazenamento em banco de dados
- Sistema anti-duplicação

## ⚠️ Status
- Reddit: ✅ Funcionando
- RSS: ✅ Funcionando
- Twitter: ❌ Bloqueado (migrando para API oficial)

## ▶️ Como rodar

```bash
python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

python manage.py migrate
python manage.py runserver