#!/usr/bin/env python3
"""
Script para publicar o pacote no PyPI.
"""

import shutil
import subprocess
import sys
from pathlib import Path


def run_command(command, description):
    """Executa um comando e trata erros."""
    print(f"\n🔄 {description}...")
    # Sem capturar a saída, para que o uv possa pedir credenciais e mostrar o progresso
    try:
        subprocess.run(command, shell=True, check=True)
        print(f"✅ {description} concluído com sucesso!")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Erro ao {description.lower()}:")
        print(f"Comando: {command}")
        return False


def clean_build():
    """Remove diretórios de build anteriores."""
    dirs_to_clean = ["build", "dist", "*.egg-info"]
    for pattern in dirs_to_clean:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                print(f"🧹 Removendo {path}")
                shutil.rmtree(path)
            elif path.is_file():
                print(f"🧹 Removendo {path}")
                path.unlink()


def check_dependencies():
    """Verifica se o uv está instalado."""
    if shutil.which("uv") is None:
        print("❌ uv não encontrado. Instale: https://docs.astral.sh/uv/getting-started/installation/")
        return False
    return True


def build_package():
    """Constrói o pacote."""
    return run_command("uv build", "Construir pacote")


def check_package():
    """Verifica o pacote construído."""
    return run_command("uvx twine check --strict dist/*", "Verificar pacote")


def upload_to_testpypi():
    """Faz upload para TestPyPI."""
    print("\n🚀 Fazendo upload para TestPyPI...")
    print("⚠️  Use o token do TestPyPI (UV_PUBLISH_TOKEN ou digite quando solicitado).")
    return run_command("uv publish --publish-url https://test.pypi.org/legacy/", "Upload para TestPyPI")


def upload_to_pypi():
    """Faz upload para PyPI."""
    print("\n🚀 Fazendo upload para PyPI...")
    print("⚠️  Use o token do PyPI (UV_PUBLISH_TOKEN ou digite quando solicitado).")
    return run_command("uv publish", "Upload para PyPI")


def main():
    """Função principal."""
    print("🚀 Iniciando processo de publicação no PyPI...")

    # Verificar dependências
    if not check_dependencies():
        sys.exit(1)

    # Limpar builds anteriores
    clean_build()

    # Construir pacote
    if not build_package():
        sys.exit(1)

    # Verificar pacote
    if not check_package():
        sys.exit(1)

    # Perguntar onde fazer upload
    print("\n📋 Onde você quer fazer o upload?")
    print("1. TestPyPI (recomendado primeiro)")
    print("2. PyPI (produção)")
    print("3. Ambos")
    print("4. Apenas construir (sem upload)")

    choice = input("\nEscolha (1-4): ").strip()

    if choice == "1":
        upload_to_testpypi()
    elif choice == "2":
        upload_to_pypi()
    elif choice == "3":
        upload_to_testpypi()
        if input("\nContinuar para PyPI? (y/n): ").lower() == "y":
            upload_to_pypi()
    elif choice == "4":
        print("✅ Pacote construído com sucesso! Arquivos em ./dist/")
    else:
        print("❌ Opção inválida!")
        sys.exit(1)

    print("\n🎉 Processo concluído!")


if __name__ == "__main__":
    main()
