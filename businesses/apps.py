from django.apps import AppConfig


class BusinessesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'businesses'

    def ready(self):
        import businesses.signals  # noqa: F401
