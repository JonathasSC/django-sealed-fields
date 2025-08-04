"""
Exemplos de uso das funcionalidades de timestamp para evitar cache de arquivos.

Este arquivo demonstra como usar as funções utilitárias para gerar URLs
com timestamp que evitam cache do navegador.
"""

from .views import get_file_url, get_file_url_with_timestamp


def exemplo_uso_timestamp():
    """
    Exemplo de como usar as funções para gerar URLs com timestamp.
    """
    
    # Parâmetros de exemplo
    app_name = "myapp"
    model_name = "MyModel"
    field_name = "image"
    uuid = "123e4567-e89b-12d3-a456-426614174000"
    
    # 1. URL sem timestamp (retro-compatibilidade)
    url_sem_timestamp = get_file_url(app_name, model_name, field_name, uuid)
    print(f"URL sem timestamp: {url_sem_timestamp}")
    # Exemplo: /serve/files/myapp/MyModel/image/123e4567-e89b-12d3-a456-426614174000/
    
    # 2. URL com timestamp atual (automático)
    url_com_timestamp = get_file_url_with_timestamp(app_name, model_name, field_name, uuid)
    print(f"URL com timestamp atual: {url_com_timestamp}")
    # Exemplo: /serve/files/myapp/MyModel/image/123e4567-e89b-12d3-a456-426614174000/1703123456/
    
    # 3. URL com timestamp específico
    timestamp_especifico = 1703123456
    url_timestamp_especifico = get_file_url_with_timestamp(
        app_name, model_name, field_name, uuid, timestamp_especifico
    )
    print(f"URL com timestamp específico: {url_timestamp_especifico}")
    # Exemplo: /serve/files/myapp/MyModel/image/123e4567-e89b-12d3-a456-426614174000/1703123456/


def exemplo_uso_template():
    """
    Exemplo de como usar em templates Django.
    """
    
    # No seu template, você pode usar assim:
    template_example = """
    <!-- URL sem timestamp (pode ser cacheada pelo navegador) -->
    <img src="{% url 'serve_files:serve_decrypted_file' app_name='myapp' model_name='MyModel' field_name='image' uuid=object.uuid %}" alt="Imagem">
    
    <!-- URL com timestamp (evita cache do navegador) -->
    <img src="{% url 'serve_files:serve_decrypted_file_with_timestamp' app_name='myapp' model_name='MyModel' field_name='image' uuid=object.uuid timestamp=timestamp %}" alt="Imagem">
    """
    
    print("Exemplo de uso em template:")
    print(template_example)


def exemplo_uso_view():
    """
    Exemplo de como usar em views Django.
    """
    
    # Em uma view, você pode fazer assim:
    view_example = """
    from django.shortcuts import render
    from .views import get_file_url_with_timestamp
    import time
    
    def minha_view(request):
        # Gerar URL com timestamp atual
        url_imagem = get_file_url_with_timestamp(
            'myapp', 'MyModel', 'image', '123e4567-e89b-12d3-a456-426614174000'
        )
        
        # Ou usar timestamp específico (ex: quando o arquivo foi modificado)
        timestamp_modificacao = int(time.time())  # ou timestamp do arquivo
        url_imagem_atualizada = get_file_url_with_timestamp(
            'myapp', 'MyModel', 'image', '123e4567-e89b-12d3-a456-426614174000',
            timestamp=timestamp_modificacao
        )
        
        context = {
            'url_imagem': url_imagem,
            'url_imagem_atualizada': url_imagem_atualizada,
        }
        return render(request, 'meu_template.html', context)
    """
    
    print("Exemplo de uso em view:")
    print(view_example)


if __name__ == "__main__":
    print("=== Exemplos de uso das funcionalidades de timestamp ===\\n")
    
    exemplo_uso_timestamp()
    print("\\n" + "="*50 + "\\n")
    
    exemplo_uso_template()
    print("\\n" + "="*50 + "\\n")
    
    exemplo_uso_view() 