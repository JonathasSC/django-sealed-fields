# Comandos para Publicar no PyPI

## Pré-requisitos

1. **Conta no PyPI**: https://pypi.org/account/register/
2. **Conta no TestPyPI**: https://test.pypi.org/account/register/
3. **API Token**: Configure um token de API em ambas as contas

## Opção 1: Usando o Script Automatizado

```bash
# Executar o script de publicação
python publish.py
```

## Opção 2: Comandos Manuais

### 1. Instalar dependências de build
```bash
pip install build twine
```

### 2. Limpar builds anteriores
```bash
# Windows
rmdir /s /q build dist *.egg-info 2>nul

# Linux/Mac
rm -rf build/ dist/ *.egg-info/
```

### 3. Construir o pacote
```bash
python -m build
```

### 4. Verificar o pacote
```bash
twine check dist/*
```

### 5. Upload para TestPyPI (recomendado primeiro)
```bash
twine upload --repository testpypi dist/*
```

### 6. Testar instalação do TestPyPI
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ django-encrypted-fields-and-files
```

### 7. Upload para PyPI (produção)
```bash
twine upload dist/*
```

## Configuração de Credenciais

### Opção A: Arquivo .pypirc
Crie um arquivo `~/.pypirc` (Linux/Mac) ou `%USERPROFILE%\.pypirc` (Windows):

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-TOKEN_AQUI

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-TOKEN_AQUI
```

### Opção B: Variáveis de Ambiente
```bash
# Windows
set TWINE_USERNAME=__token__
set TWINE_PASSWORD=pypi-TOKEN_AQUI

# Linux/Mac
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-TOKEN_AQUI
```

## Verificação Pós-Upload

1. **TestPyPI**: https://test.pypi.org/project/django-encrypted-fields-and-files/
2. **PyPI**: https://pypi.org/project/django-encrypted-fields-and-files/

## Comandos Rápidos (Windows PowerShell)

```powershell
# Limpar e construir
Remove-Item -Recurse -Force build, dist, *.egg-info -ErrorAction SilentlyContinue
python -m build

# Verificar
twine check dist/*

# Upload para TestPyPI
twine upload --repository testpypi dist/*

# Upload para PyPI
twine upload dist/*
```

## Troubleshooting

### Erro de autenticação
- Verifique se o token está correto
- Use `__token__` como username e `pypi-TOKEN_AQUI` como password

### Erro de versão já existente
- Incremente a versão no `setup.py` e `pyproject.toml`

### Erro de dependências
- Verifique se todas as dependências estão listadas em `install_requires`

### Erro de arquivos faltando
- Verifique se o `MANIFEST.in` está correto
- Execute `python setup.py sdist` para verificar arquivos incluídos 