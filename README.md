# django-sealed-fields

[![CI](https://github.com/JonathasSC/django-sealed-fields/actions/workflows/ci.yml/badge.svg)](https://github.com/JonathasSC/django-sealed-fields/actions/workflows/ci.yml)

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
- Django 4.2, 5.2, 6.0 ou 6.1
- `cryptography` e `pillow` (instaladas automaticamente)

## Instalação

```bash
uv add django-sealed-fields
# ou
pip install django-sealed-fields
```

## Configuração

1. **Adicione a chave de criptografia no arquivo `settings.py`:**

   No arquivo `settings.py`, defina a chave de criptografia `ENCRYPTION_KEY`:

   ```python
   ENCRYPTION_KEY = os.environ["ENCRYPTION_KEY"]  # chave Fernet
   DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 * 1024 * 1024
   SERVE_DECRYPTED_FILE_URL_BASE = 'arquivos/'  # prefixo das URLs que servem arquivos
   ```

   Gere uma chave Fernet válida com:

   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

   **Importante**: A chave de criptografia deve ser mantida em segredo. Use uma chave única para o seu projeto e não compartilhe publicamente.

2. **Adicione o app `sealed_fields.serve` à lista de apps instalados** (necessário apenas para servir arquivos descriptografados):

   No arquivo `settings.py`, adicione o app à lista `INSTALLED_APPS`:

   ```python
   INSTALLED_APPS = [
       # outros apps
       'sealed_fields.serve',
   ]
   ```

## Uso

### Modelos

Agora, você pode usar os campos criptografados em seus modelos Django da seguinte forma:

```python
from django.db import models
from sealed_fields import EncryptedFileField, EncryptedImageField, EncryptedIntegerField

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

Inclua as URLs do app `sealed_fields.serve` no `urls.py` do projeto:

```python
urlpatterns = [
    path("", include("sealed_fields.serve.urls")),
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

Para gerar a URL de um arquivo em views ou templates:

```python
from sealed_fields.serve.views import get_file_url, get_file_url_with_timestamp

url = get_file_url("meuapp", "MeuModelo", "campo_imagem", obj.uuid)
# Com timestamp na URL, para evitar cache do navegador após atualizar o arquivo
url = get_file_url_with_timestamp("meuapp", "MeuModelo", "campo_imagem", obj.uuid)
```

```django
<img src="{% url 'sealed_fields:serve_decrypted_file' app_name='meuapp' model_name='MeuModelo' field_name='campo_imagem' uuid=obj.uuid %}">
```

## Migrando do `django-encrypted-fields-and-files`

Os dados já gravados continuam compatíveis (mesma chave `ENCRYPTION_KEY` e mesmo formato), mas os nomes de import mudaram:

| Antes | Agora |
|---|---|
| `pip install django-encrypted-fields-and-files` | `pip install django-sealed-fields` |
| `from encrypted_fields.encrypted_fields import ...` | `from sealed_fields import ...` |
| `from encrypted_fields.encrypted_files import ...` | `from sealed_fields import ...` |
| `INSTALLED_APPS = [..., "serve_files"]` | `INSTALLED_APPS = [..., "sealed_fields.serve"]` |
| `include("serve_files.urls")` | `include("sealed_fields.serve.urls")` |
| `{% url 'serve_files:...' %}` / `reverse("serve_files:...")` | `{% url 'sealed_fields:...' %}` / `reverse("sealed_fields:...")` |
| `from serve_files.views import get_file_url` | `from sealed_fields.serve.views import get_file_url` |

As migrações já existentes no seu projeto importam os campos pelo caminho antigo. Atualize-as com:

```bash
grep -rl "encrypted_fields" --include="*.py" */migrations/ | xargs sed -i \
  -e "s/encrypted_fields\.encrypted_fields/sealed_fields.fields/g" \
  -e "s/encrypted_fields\.encrypted_files/sealed_fields.files/g" \
  -e "s/^import encrypted_fields$/import sealed_fields/"
```

Depois, rode `python manage.py makemigrations --check` para confirmar que nenhuma migração nova é necessária.

Mudanças de comportamento em relação à versão original:

- A view de arquivos exige login e permissão (veja [Servindo arquivos descriptografados](#servindo-arquivos-descriptografados)).
- `EncryptedDateTimeField`, `EncryptedTimeField`, `EncryptedDecimalField`, `EncryptedUUIDField` e `EncryptedJSONField` passaram a funcionar. Valores de `EncryptedUUIDField` gravados pela versão original ficaram em texto puro e não podem ser lidos.

## Desenvolvimento

O projeto usa [uv](https://docs.astral.sh/uv/) para gerenciar o ambiente e as dependências, e [Ruff](https://docs.astral.sh/ruff/) como linter.

```bash
git clone https://github.com/JonathasSC/django-sealed-fields
cd django-sealed-fields
uv sync                           # cria o .venv com o pacote e as dependências de desenvolvimento

uv run python runtests.py         # testes
uv run ruff check .               # lint
uv run ruff check --fix .         # corrige automaticamente o que for possível
```

Para testar com outra versão do Django ou do Python:

```bash
uv sync --python 3.13
uv pip install "django~=6.1.0"
uv run --no-sync python runtests.py
```

Ao alterar as dependências no `pyproject.toml`, rode `uv lock` e inclua o `uv.lock` no commit.

## Contribuição

Sinta-se à vontade para contribuir! Para sugestões ou melhorias, siga os seguintes passos:

1. Faça um fork deste repositório.
2. Crie uma branch (`git checkout -b feature-nome-da-sua-feature`).
3. Garanta que `uv run python runtests.py` e `uv run ruff check .` passam.
4. Comite suas mudanças e envie a branch para o seu fork.
5. Abra um Pull Request. O CI roda o lint, os testes em todas as versões suportadas do Django e o build do pacote.

## Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para mais detalhes.
