from django.urls import path
from .views import *
from django.conf import settings

app_name = 'serve_files'

# Garantir que a variável SERVE_DECRYPTED_FILE_URL_BASE esteja no settings
if not hasattr(settings, 'SERVE_DECRYPTED_FILE_URL_BASE'):
    raise ValueError("SERVE_DECRYPTED_FILE_URL_BASE must be set in your environment.")

# Base URL para servir os arquivos descriptografados (remover barra no final, se existir)
base_url_serve_decrypted_file = settings.SERVE_DECRYPTED_FILE_URL_BASE.rstrip('/')

# Criar as URLs - mantendo retro-compatibilidade
urlpatterns = [
    # URL original para retro-compatibilidade
    path(f'{base_url_serve_decrypted_file}/<str:app_name>/<str:model_name>/<str:field_name>/<str:uuid>/', serve_decrypted_file, name='serve_decrypted_file'),
    
    # Nova URL com timestamp opcional para evitar cache
    path(f'{base_url_serve_decrypted_file}/<str:app_name>/<str:model_name>/<str:field_name>/<str:uuid>/<int:timestamp>/', serve_decrypted_file, name='serve_decrypted_file_with_timestamp'),
]
