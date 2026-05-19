from django.apps import AppConfig


class ModelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.model'
    label = 'streaming'
    verbose_name = 'Streaming Models'
