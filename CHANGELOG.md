# Changelog

Todas as mudanças relevantes deste projeto são documentadas aqui.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto usa [versionamento semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

## [0.1.0] - 2026-09-25

Primeira versão do `django-sealed-fields`, fork de [`django-encrypted-fields-and-files`](https://github.com/D3NKYT0/django-encrypted-fields) 0.1.12. Veja o guia de migração no README.

### Adicionado

- Rotação de chave: `ENCRYPTION_KEY` aceita uma lista de chaves (a primeira criptografa, todas descriptografam) e o comando `rotate_encryption_key` recriptografa campos e arquivos.
- Regra de acesso configurável na view de arquivos (`SERVE_DECRYPTED_FILE_PERMISSION_CHECK`).
- Suporte oficial a Django 4.2, 5.2, 6.0 e 6.1 e Python 3.10 a 3.14.
- Suíte de testes e CI.

### Alterado

- Pacotes de import renomeados: `encrypted_fields` → `sealed_fields` e `serve_files` → `sealed_fields.serve`.
- Arquivos são descriptografados apenas quando lidos; consultas ao banco não acessam mais o storage.
- Chave ausente ou inválida gera `ImproperlyConfigured` ao usar um campo, em vez de `ValueError` ao importar os models.
- Removido o limite `cryptography<45`.

### Corrigido

- **Segurança:** a view de arquivos servia qualquer arquivo, de qualquer modelo, sem autenticação. Agora exige login e a permissão `view` do modelo, e aceita apenas campos de arquivo.
- **Segurança:** `EncryptedUUIDField` e `EncryptedDecimalField` (no Django 4.2) gravavam o valor sem criptografia.
- `EncryptedDateTimeField`, `EncryptedTimeField`, `EncryptedDecimalField`, `EncryptedUUIDField` e `EncryptedJSONField` falhavam ao salvar ou ao ler.
- `EncryptedFileField` falhava em todo save (`_encrypt_image` inexistente).
- `EncryptedImageField` falhava no Django 6.
- Salvar uma instância duplicava o arquivo no storage.
- Um arquivo ausente no storage derrubava a consulta inteira.
- `full_clean` não validava os valores dos campos criptografados.
- `from sealed_fields import *` sobrescrevia nomes como `datetime`.
- A view expunha mensagens de exceções internas.

[Não lançado]: https://github.com/JonathasSC/django-sealed-fields/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/JonathasSC/django-sealed-fields/releases/tag/v0.1.0
