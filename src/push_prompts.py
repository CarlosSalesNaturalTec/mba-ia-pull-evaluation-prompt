"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

SIMPLIFICADO: Código mais limpo e direto ao ponto.
"""

import os
import sys
from dotenv import load_dotenv
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header

load_dotenv()

PROMPT_NAME = "prompts/bug_to_user_story_v1.yml"

def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    ...


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    ...


def main():
    """Função principal"""
    print_section_header("Pushing Prompts no LangSmith Prompt Hub")

    print("🔍 Validando variáveis de ambiente...")
    if not check_env_vars(["LANGSMITH_API_KEY"]): return 1
    
    print("Carregando prompt otimizado...")
    prompt_data = load_yaml(PROMPT_NAME)
    if not prompt_data: return 1

    print("Efetuando validação do prompt otimizado...")
    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt não passou na validação. Corrija os erros e tente novamente.")
        for error in errors:
            print(f"   - {error}")
        return 1

    print("✅ Prompt validado com sucesso! Iniciando push...")
    success = push_prompt_to_langsmith(PROMPT_NAME, prompt_data)
    if success:
        print("✅ Push realizado com sucesso!")
        return 0
    else:
        print("❌ Falha ao realizar Push.")
        return 1
        

if __name__ == "__main__":
    sys.exit(main())
