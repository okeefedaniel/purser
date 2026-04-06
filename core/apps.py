from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'
    label = 'purser_core'
    verbose_name = 'Purser Core'
    default_auto_field = 'django.db.models.BigAutoField'
