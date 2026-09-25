# Publicação no PyPI

## Fluxo recomendado: GitHub Actions (Trusted Publishing)

O workflow `.github/workflows/release.yml` publica sem tokens, usando [Trusted Publishing](https://docs.pypi.org/trusted-publishers/).

### Configuração (uma única vez)

Cadastre um *pending publisher* em cada índice, em **Your account → Publishing → Add a new pending publisher → GitHub**:

| Campo | PyPI (https://pypi.org/manage/account/publishing/) | TestPyPI (https://test.pypi.org/manage/account/publishing/) |
|---|---|---|
| PyPI Project Name | `django-sealed-fields` | `django-sealed-fields` |
| Owner | `JonathasSC` | `JonathasSC` |
| Repository name | `django-sealed-fields` | `django-sealed-fields` |
| Workflow name | `release.yml` | `release.yml` |
| Environment name | `pypi` | `testpypi` |

Os ambientes `pypi` e `testpypi` já existem no repositório. O `pypi` só aceita tags `v*` e exige aprovação manual antes de publicar.

### Publicar uma versão

1. Atualize `version` no `pyproject.toml` e mova as notas de `[Não lançado]` para a nova versão no `CHANGELOG.md` (via PR).
2. Opcional: teste no TestPyPI em **Actions → Release → Run workflow** (roda o CI e publica só no TestPyPI).
3. Crie e envie a tag a partir da `main` atualizada:

   ```bash
   git checkout main && git pull
   git tag v0.1.0
   git push origin v0.1.0
   ```

4. O workflow roda o CI, confere se a tag bate com a versão do `pyproject.toml`, publica no TestPyPI e aguarda sua aprovação em **Actions → Release → Review deployments** para publicar no PyPI. Por fim, cria a GitHub Release com as notas do `CHANGELOG.md`.

> Uma versão publicada no PyPI não pode ser substituída, nem depois de apagada. Em caso de erro, publique uma nova versão.

---

## Fluxo manual (alternativa)

Pré-requisitos: [uv](https://docs.astral.sh/uv/getting-started/installation/), contas no [PyPI](https://pypi.org/account/register/) e no [TestPyPI](https://test.pypi.org/account/register/) e um token de API em cada uma.

### Script interativo

```bash
uv run --no-project python publish.py
```

### Comandos

#### 1. Limpar builds anteriores
```bash
# Linux/Mac
rm -rf build/ dist/ *.egg-info/

# Windows (PowerShell)
Remove-Item -Recurse -Force build, dist, *.egg-info -ErrorAction SilentlyContinue
```

#### 2. Construir o pacote
```bash
uv build
```

#### 3. Verificar o pacote
```bash
uvx twine check --strict dist/*
```

#### 4. Upload para TestPyPI (recomendado primeiro)
```bash
uv publish --publish-url https://test.pypi.org/legacy/ --token pypi-TOKEN_DO_TESTPYPI
```

#### 5. Testar instalação do TestPyPI
```bash
uv pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ django-sealed-fields
```

#### 6. Upload para PyPI (produção)
```bash
uv publish --token pypi-TOKEN_DO_PYPI
```

### Credenciais

Em vez de passar `--token` na linha de comando, defina a variável de ambiente `UV_PUBLISH_TOKEN`:

```bash
# Linux/Mac
export UV_PUBLISH_TOKEN=pypi-TOKEN_AQUI

# Windows (PowerShell)
$env:UV_PUBLISH_TOKEN = "pypi-TOKEN_AQUI"
```

Lembre-se de que o PyPI e o TestPyPI usam tokens diferentes.

## Verificação pós-publicação

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
