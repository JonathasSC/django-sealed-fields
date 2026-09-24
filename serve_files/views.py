import logging
import os
import time
from mimetypes import guess_type

from django.apps import apps
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import FieldDoesNotExist, FieldError, ValidationError
from django.db import models
from django.http import HttpResponse
from django.urls import reverse
from django.utils.http import content_disposition_header
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


def default_permission_check(user, obj, field_name):
    """
    Permissão padrão para servir um arquivo: o usuário precisa da permissão `view` do modelo.

    Para outra regra (por exemplo, permitir que o dono do objeto veja o próprio arquivo),
    defina SERVE_DECRYPTED_FILE_PERMISSION_CHECK no settings com o caminho de uma função
    com a mesma assinatura.
    """
    opts = obj._meta
    return user.has_perm(f"{opts.app_label}.view_{opts.model_name}")


def get_permission_check():
    path = getattr(settings, "SERVE_DECRYPTED_FILE_PERMISSION_CHECK", None)
    return import_string(path) if path else default_permission_check


@login_required
def serve_decrypted_file(request, app_name, model_name, field_name, uuid, timestamp=None):
    """
    View para descriptografar e retornar o arquivo (imagem ou qualquer outro) com cache de 5 minutos.
    Suporta timestamp opcional para evitar cache do navegador.
    """
    try:
        model = apps.get_model(app_name, model_name)
    except (LookupError, ValueError):
        return HttpResponse("Modelo não encontrado.", status=404)

    try:
        field = model._meta.get_field(field_name)
    except FieldDoesNotExist:
        return HttpResponse("Campo não encontrado.", status=404)
    if not isinstance(field, models.FileField):
        return HttpResponse("Campo não encontrado.", status=404)

    # Adia os campos de arquivo para descriptografar apenas o solicitado, e só se não houver cache
    file_fields = [f.name for f in model._meta.concrete_fields if isinstance(f, models.FileField)]
    try:
        obj = model._default_manager.defer(*file_fields).filter(uuid=uuid).first()
    except (FieldError, ValidationError, ValueError):
        obj = None
    if not obj:
        return HttpResponse("Objeto não encontrado.", status=404)

    if not get_permission_check()(request.user, obj, field_name):
        return HttpResponse("Acesso negado.", status=403)

    try:
        # Tenta recuperar o arquivo do cache (ignora timestamp para cache)
        cache_key = f"{app_name}_{model_name}_{field_name}_{uuid}"
        response = cache.get(cache_key)

        if response is None:
            file = getattr(obj, field_name)
            if not file:
                return HttpResponse("Arquivo não encontrado.", status=404)

            file.open("rb")
            try:
                content = file.read()
            finally:
                file.close()

            filename = os.path.basename(file.name)
            mime_type, _ = guess_type(filename)

            response = HttpResponse(content, content_type=mime_type or "application/octet-stream")
            response["Content-Disposition"] = content_disposition_header(False, filename)
            response["X-Content-Type-Options"] = "nosniff"

            # Armazena a resposta no cache por 5 minutos
            cache.set(cache_key, response, timeout=300)
    except Exception:
        logger.exception("Erro ao servir arquivo %s.%s.%s (%s)", app_name, model_name, field_name, uuid)
        return HttpResponse("Erro ao processar o arquivo.", status=500)

    # Adiciona headers para evitar cache do navegador
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"

    # Se timestamp foi fornecido, adiciona header ETag baseado no timestamp
    if timestamp:
        response["ETag"] = f'"{timestamp}"'

    return response


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
