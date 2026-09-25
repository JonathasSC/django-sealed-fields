# Comandos para Publicar no PyPI

## Pré-requisitos

1. **uv**: https://docs.astral.sh/uv/getting-started/installation/
2. **Conta no PyPI**: https://pypi.org/account/register/
3. **Conta no TestPyPI**: https://test.pypi.org/account/register/
4. **API Token**: Configure um token de API em ambas as contas

## Opção 1: Usando o Script Automatizado

```bash
uv run --no-project python publish.py
```

## Opção 2: Comandos Manuais

### 1. Limpar builds anteriores
```bash
# Linux/Mac
rm -rf build/ dist/ *.egg-info/

# Windows (PowerShell)
Remove-Item -Recurse -Force build, dist, *.egg-info -ErrorAction SilentlyContinue
```

### 2. Construir o pacote
```bash
uv build
```

### 3. Verificar o pacote
```bash
uvx twine check --strict dist/*
```

### 4. Upload para TestPyPI (recomendado primeiro)
```bash
uv publish --publish-url https://test.pypi.org/legacy/ --token pypi-TOKEN_DO_TESTPYPI
```

### 5. Testar instalação do TestPyPI
```bash
uv pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ django-sealed-fields
```

### 6. Upload para PyPI (produção)
```bash
uv publish --token pypi-TOKEN_DO_PYPI
```

## Configuração de Credenciais

Em vez de passar `--token` na linha de comando, defina a variável de ambiente `UV_PUBLISH_TOKEN`:

```bash
# Linux/Mac
export UV_PUBLISH_TOKEN=pypi-TOKEN_AQUI

# Windows (PowerShell)
$env:UV_PUBLISH_TOKEN = "pypi-TOKEN_AQUI"
```

Lembre-se de que o PyPI e o TestPyPI usam tokens diferentes.

## Verificação Pós-Upload

1. **TestPyPI**: https://test.pypi.org/project/django-sealed-fields/
2. **PyPI**: https://pypi.org/project/django-sealed-fields/

## Troubleshooting

### Erro de autenticação
- Verifique se o token é da conta certa (PyPI ou TestPyPI)
- Confira se `UV_PUBLISH_TOKEN` não contém um token antigo

### Erro de versão já existente
- Incremente a versão no `pyproject.toml`

### Erro de dependências
- Verifique se todas as dependências estão listadas em `dependencies` no `pyproject.toml`
- Rode `uv lock` depois de alterar as dependências

### Erro de arquivos faltando
- Verifique se o `MANIFEST.in` está correto
