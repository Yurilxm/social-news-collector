from django.db import models

class Tweet(models.Model):
    username = models.CharField(max_length=255, db_index=True)
    content = models.TextField()
    date = models.DateTimeField(db_index=True)
    url = models.URLField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['username', '-date']),
        ]

    def __str__(self):
        return f"@{self.username}: {self.content[:50]}..."
    

class RedditPost(models.Model):
    reddit_id = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=500)
    content = models.TextField(blank=True)
    author = models.CharField(max_length=255)
    subreddit = models.CharField(max_length=255, db_index=True)
    url = models.URLField(unique=True)
    score = models.IntegerField(default=0)
    num_comments = models.IntegerField(default=0)
    created_utc = models.DateTimeField()
    collected_at = models.DateTimeField(auto_now_add=True)
    is_news = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_utc']
        indexes = [
            models.Index(fields=['subreddit', '-created_utc']),
            models.Index(fields=['author', '-created_utc']),
            models.Index(fields=['-score']),
        ]
    
    def __str__(self):
        return f"[r/{self.subreddit}] {self.title[:80]}"


class RedditComment(models.Model):
    """Comentários coletados de posts monitorados"""
    comment_id = models.CharField(max_length=50, unique=True)
    post = models.ForeignKey(RedditPost, on_delete=models.CASCADE, related_name='comments')
    author = models.CharField(max_length=255)
    content = models.TextField()
    score = models.IntegerField(default=0)
    created_utc = models.DateTimeField()
    collected_at = models.DateTimeField(auto_now_add=True)
    matched_keywords = models.CharField(max_length=500, blank=True)
    
    class Meta:
        ordering = ['-score']
        indexes = [
            models.Index(fields=['post', '-score']),
            models.Index(fields=['author', '-created_utc']),
        ]
    
    def __str__(self):
        return f"💬 u/{self.author}: {self.content[:80]}"


class MonitorConfig(models.Model):
    """Configuração de monitoramento automático"""
    MONITOR_TYPES = [
        ('subreddit', 'Subreddit'),
        ('user', 'Perfil de Usuário'),
    ]
    
    name = models.CharField(max_length=255, verbose_name="Nome do monitor")
    monitor_type = models.CharField(
        max_length=20, 
        choices=MONITOR_TYPES, 
        default='subreddit',
        verbose_name="Tipo de monitor"
    )
    target = models.CharField(
        max_length=255, 
        verbose_name="Alvo (subreddit ou usuário)",
        help_text="Ex: 'brasil' para r/brasil ou 'username' para u/username"
    )
    keywords = models.TextField(
        blank=True, 
        help_text="Palavras-chave separadas por vírgula",
        verbose_name="Palavras-chave"
    )
    min_score = models.IntegerField(default=10, verbose_name="Score mínimo")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    interval_minutes = models.IntegerField(default=5, verbose_name="Intervalo (minutos)")
    start_date = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Data inicial",
        help_text="Coletar posts desde esta data"
    )
    last_run = models.DateTimeField(null=True, blank=True, verbose_name="Última execução")
    created_at = models.DateTimeField(auto_now_add=True)
    collect_comments = models.BooleanField(
        default=False,
        verbose_name="Coletar comentários"
    )
    
    class Meta:
        verbose_name = "Configuração de Monitor"
        verbose_name_plural = "Configurações de Monitores"
    
    def __str__(self):
        type_label = 'r/' if self.monitor_type == 'subreddit' else 'u/'
        return f"{self.name} - {type_label}{self.target}"


class FilteredPost(models.Model):
    """Posts filtrados por relevância"""
    reddit_post = models.ForeignKey(RedditPost, on_delete=models.CASCADE)
    monitor = models.ForeignKey(MonitorConfig, on_delete=models.CASCADE)
    matched_keywords = models.CharField(max_length=500, blank=True)
    relevance_score = models.FloatField(default=0.0)
    is_sent = models.BooleanField(default=False, verbose_name="Notificado")
    collected_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['reddit_post', 'monitor']
        verbose_name = "Post Filtrado"
        verbose_name_plural = "Posts Filtrados"
    
    def __str__(self):
        return f"[{self.monitor.name}] {self.reddit_post.title[:80]}"


class ThreadsPost(models.Model):
    post_id = models.CharField(max_length=100, unique=True)
    username = models.CharField(max_length=255, db_index=True)
    content = models.TextField()
    likes = models.IntegerField(default=0)
    replies = models.IntegerField(default=0)
    created_at = models.DateTimeField()
    url = models.URLField(unique=True)
    collected_at = models.DateTimeField(auto_now_add=True)
    is_news = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['username', '-created_at']),
        ]
    
    def __str__(self):
        return f"@{self.username}: {self.content[:80]}"
    


class RSSSource(models.Model):
    """Fonte de feed RSS"""
    name = models.CharField(max_length=255, verbose_name="Nome da fonte")
    url = models.URLField(unique=True, verbose_name="URL do feed")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    last_fetch = models.DateTimeField(null=True, blank=True, verbose_name="Última coleta")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Fonte RSS"
        verbose_name_plural = "Fontes RSS"
    
    def __str__(self):
        return f"📡 {self.name}"


class RSSEntry(models.Model):
    """Entrada de feed RSS coletada"""
    entry_id = models.CharField(max_length=500, unique=True)
    source = models.ForeignKey(RSSSource, on_delete=models.CASCADE)
    title = models.CharField(max_length=500)
    content = models.TextField(blank=True)
    author = models.CharField(max_length=255, blank=True)
    url = models.URLField()
    published_at = models.DateTimeField()
    collected_at = models.DateTimeField(auto_now_add=True)
    is_news = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['source', '-published_at']),
            models.Index(fields=['-published_at']),
        ]
        verbose_name = "Entrada RSS"
        verbose_name_plural = "Entradas RSS"
    
    def __str__(self):
        return f"[{self.source.name}] {self.title[:80]}"