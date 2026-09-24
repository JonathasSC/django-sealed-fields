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

Cada campo aceita os mesmos argumentos e faz a mesma validação do campo equivalente do Django:

| Campo criptografado | Equivalente no Django |
|---|---|
| `EncryptedIntegerField` | `IntegerField` |
| `EncryptedFloatField` | `FloatField` |
| `EncryptedDecimalField` | `DecimalField` |
| `EncryptedBooleanField` | `BooleanField` |
| `EncryptedCharField` | `CharField` |
| `EncryptedTextField` | `TextField` |
| `EncryptedEmailField` | `EmailField` |
| `EncryptedURLField` | `URLField` |
| `EncryptedDateField` | `DateField` |
| `EncryptedDateTimeField` | `DateTimeField` |
| `EncryptedTimeField` | `TimeField` |
| `EncryptedUUIDField` | `UUIDField` |
| `EncryptedJSONField` | `JSONField` |
| `EncryptedFileField` | `FileField` (o conteúdo do arquivo é criptografado no storage) |
| `EncryptedImageField` | `ImageField` (o conteúdo da imagem é criptografado no storage) |

Os valores são criptografados automaticamente antes de serem salvos no banco de dados e descriptografados quando acessados.

### Limitações

- A criptografia Fernet não é determinística: o mesmo valor gera textos cifrados diferentes. Por isso, filtros por valor (`filter(campo="x")`), `unique=True` e ordenação pelo campo criptografado não funcionam.
- Todos os valores são gravados em colunas de texto. Datas com fuso horário são convertidas para UTC antes da criptografia.
- Consultas por chave em `EncryptedJSONField` (`campo__chave=...`) não funcionam, pelo mesmo motivo dos filtros.

### Servindo arquivos descriptografados

Inclua as URLs do app `serve_files` no `urls.py` do projeto:

```python
urlpatterns = [
    path("", include("serve_files.urls")),
]
```

A view exige usuário autenticado (usuários anônimos são redirecionados para o `LOGIN_URL`) e, por padrão, a permissão `view` do modelo (por exemplo, `meuapp.view_meumodelo`). Apenas campos de arquivo do modelo podem ser servidos, e o objeto é buscado pelo campo `uuid`.

Para usar outra regra de acesso, aponte `SERVE_DECRYPTED_FILE_PERMISSION_CHECK` para uma função que recebe o usuário, o objeto e o nome do campo:

```python
# settings.py
SERVE_DECRYPTED_FILE_PERMISSION_CHECK = "meuapp.permissions.pode_ver_arquivo"

# meuapp/permissions.py
def pode_ver_arquivo(user, obj, field_name):
    return obj.dono_id == user.id or user.has_perm("meuapp.view_meumodelo")
```

## Testes

```bash
pip install -e .
python runtests.py
```


## Contribuição

Sinta-se à vontade para contribuir! Para sugestões ou melhorias, siga os seguintes passos:

1. Faça um fork deste repositório.
2. Crie uma branch (`git checkout -b feature-nome-da-sua-feature`).
3. Comite suas mudanças (`git commit -am 'Adicionando nova funcionalidade'`).
4. Envie para o repositório remoto (`git push origin feature-nome-da-sua-feature`).
5. Abra um Pull Request.

## Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para mais detalhes.
