from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required

from django.apps import apps
from django.http import HttpResponse
from django.db.models.fields.files import FieldFile
from mimetypes import guess_type
from django.core.cache import cache
import time
from django.urls import reverse

from encrypted_fields.encrypted_fields import *
from encrypted_fields.encrypted_files import *


# Create your views here.
def serve_decrypted_file(request, app_name, model_name, field_name, uuid, timestamp=None):
    """
    View para descriptografar e retornar o arquivo (imagem ou qualquer outro) com cache de 5 minutos.
    Suporta timestamp opcional para evitar cache do navegador.
    """
    try:
        # Tenta recuperar o arquivo do cache (ignora timestamp para cache)
        cache_key = f"{app_name}_{model_name}_{field_name}_{uuid}"
        cached_file = cache.get(cache_key)

        if cached_file:
            response = cached_file
        else:
            # Valida se o app existe
            if app_name not in apps.app_configs:
                return HttpResponse("App não encontrado.", status=404)

            # Obtém o modelo dinamicamente a partir do nome
            model = apps.get_model(app_name, model_name)
            if not model:
                return HttpResponse("Modelo não encontrado.", status=404)
            
            # Busca o objeto pelo ID (pk)
            obj = model.objects.filter(uuid=uuid).first()
            if not obj:
                return HttpResponse("Objeto não encontrado.", status=404)
            
            # Obtém o campo do objeto dinamicamente
            file_field = getattr(obj, field_name, None)
            if not file_field:
                return HttpResponse("Campo não encontrado.", status=404)
            
            # Verifica se o campo é do tipo EncryptedFileField ou EncryptedImageField
            if isinstance(file_field, (EncryptedFileField, EncryptedImageField)):
                # Chama a descriptografia via from_db_value
                decrypted_file = file_field.from_db_value(file_field.name, None, None)
                if not decrypted_file:
                    return HttpResponse("Erro ao descriptografar o arquivo.", status=500)
            elif isinstance(file_field, (FieldFile)):
                # Se for um FileField ou ImageField normal, abre o arquivo associado
                decrypted_file = file_field.file
            else:
                return HttpResponse("Campo não é do tipo FieldFile.", status=400)

            # Determina o tipo MIME do arquivo
            mime_type, _ = guess_type(decrypted_file.name)
            
            # Cria a resposta com o arquivo
            response = HttpResponse(decrypted_file.read(), content_type=mime_type)
            response['Content-Disposition'] = f'inline; filename="{decrypted_file.name}"'

            # Armazena a resposta no cache por 5 minutos
            cache.set(cache_key, response, timeout=300)

        # Adiciona headers para evitar cache do navegador
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        # Se timestamp foi fornecido, adiciona header ETag baseado no timestamp
        if timestamp:
            response['ETag'] = f'"{timestamp}"'

        return response
        
    except Exception as e:
        return HttpResponse(f"Erro: {e}", status=500)


def get_file_url_with_timestamp(app_name, model_name, field_name, uuid, timestamp=None):
    """
    Função utilitária para gerar URLs de arquivos com timestamp opcional.
    
    Args:
        app_name (str): Nome do app Django
        model_name (str): Nome do modelo
        field_name (str): Nome do campo do arquivo
        uuid (str): UUID do objeto
        timestamp (int, optional): Timestamp para evitar cache. Se None, usa timestamp atual.
    
    Returns:
        str: URL completa do arquivo
    """
    if timestamp is None:
        timestamp = int(time.time())
    
    return reverse('serve_files:serve_decrypted_file_with_timestamp', kwargs={
        'app_name': app_name,
        'model_name': model_name,
        'field_name': field_name,
        'uuid': uuid,
        'timestamp': timestamp
    })


def get_file_url(app_name, model_name, field_name, uuid):
    """
    Função utilitária para gerar URLs de arquivos sem timestamp (retro-compatibilidade).
    
    Args:
        app_name (str): Nome do app Django
        model_name (str): Nome do modelo
        field_name (str): Nome do campo do arquivo
        uuid (str): UUID do objeto
    
    Returns:
        str: URL completa do arquivo
    """
    return reverse('serve_files:serve_decrypted_file', kwargs={
        'app_name': app_name,
        'model_name': model_name,
        'field_name': field_name,
        'uuid': uuid
    })
