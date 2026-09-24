# django-sealed-fields

> Fork de [django-encrypted-fields](https://github.com/D3NKYT0/django-encrypted-fields) (pacote PyPI `django-encrypted-fields-and-files`), de Daniel Amaral, mantido por Jonathas Cardoso com correções e melhorias.

Uma biblioteca Django para criptografar e descriptografar campos em modelos (ORM), incluindo tipos de dados simples, arquivos e imagens. 

Esta biblioteca utiliza o módulo `cryptography.fernet` para garantir a criptografia simétrica, protegendo dados sensíveis de maneira simples e eficaz.

## Funcionalidades

- Criptografa campos de tipos de dados como `IntegerField`, `FloatField`, `CharField`, `BooleanField`, entre outros.
- Suporte a campos de arquivo (`FileField`) e imagens (`ImageField`) com criptografia.
- Integração fácil com o ORM do Django, sem necessidade de alterações no modelo.
- Segurança robusta utilizando o `cryptography.fernet`.

## Requisitos

- Python 3.10 ou superior
- Django 4.2 ou superior
- Biblioteca `cryptography`
- Biblioteca `pillow`
- Biblioteca `django`

## Instalação

Para instalar a biblioteca, basta adicionar o pacote no seu projeto ou instalá-lo via `pip`.

### Usando `pip`:

```bash
pip install django-sealed-fields
```

### Manualmente:

1. Baixe o código fonte ou clone o repositório:
   
   ```bash
   git clone https://github.com/JonathasSC/django-sealed-fields
   ```

2. Instale os requisitos:
   
   ```bash
   pip install -r requirements.txt
   ```

## Configuração

1. **Adicione a chave de criptografia no arquivo `settings.py`:**

   No arquivo `settings.py`, defina a chave de criptografia `ENCRYPTION_KEY`:

   ```python
   ENCRYPTION_KEY = os.environ["ENCRYPTION_KEY"]  # chave Fernet
   DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 * 1024 * 1024
   SERVE_DECRYPTED_FILE_URL_BASE =  'patch/here/'
   ```

   Gere uma chave Fernet válida com:

   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

   **Importante**: A chave de criptografia deve ser mantida em segredo. Use uma chave única para o seu projeto e não compartilhe publicamente.

2. **Adicione o app `serve_files` à lista de apps instalados** (necessário apenas para servir arquivos descriptografados):

   No arquivo `settings.py`, adicione o app à lista `INSTALLED_APPS`:

   ```python
   INSTALLED_APPS = [
       # outros apps
       'serve_files',
   ]
   ```

## Uso

### Modelos

Agora, você pode usar os campos criptografados em seus modelos Django da seguinte forma:

```python
from django.db import models
from encrypted_fields.encrypted_fields import *
from encrypted_fields.encrypted_files import *

class MeuModelo(models.Model):
    campo_inteiro = EncryptedIntegerField()
    campo_arquivo = EncryptedFileField(upload_to='arquivos/')
    campo_imagem = EncryptedImageField(upload_to='imagens/')
```

### Funcionalidade dos campos:

- **`EncryptedIntegerField`**: Campo para armazenar valores inteiros criptografados.
- **`EncryptedFileField`**: Campo para armazenar arquivos criptografados.
- **`EncryptedImageField`**: Campo para armazenar imagens criptografadas.

Os valores são criptografados automaticamente antes de serem salvos no banco de dados e descriptografados quando acessados.


## Contribuição

Sinta-se à vontade para contribuir! Para sugestões ou melhorias, siga os seguintes passos:

1. Faça um fork deste repositório.
2. Crie uma branch (`git checkout -b feature-nome-da-sua-feature`).
3. Comite suas mudanças (`git commit -am 'Adicionando nova funcionalidade'`).
4. Envie para o repositório remoto (`git push origin feature-nome-da-sua-feature`).
5. Abra um Pull Request.

## Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para mais detalhes.
