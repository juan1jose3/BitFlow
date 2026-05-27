from django.apps import AppConfig


class ModelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.model'
    label = 'streaming'
    verbose_name = 'Streaming Models'

    def ready(self):
        import backend.model.analytics_models  # noqa: F401 — registers models
