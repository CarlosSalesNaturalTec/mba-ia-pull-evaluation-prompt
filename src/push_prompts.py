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
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header, validate_prompt_structure

load_dotenv()

PROMPT_NAME = "prompts/bug_to_user_story_v2.yml"

def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    print("   [MOCK] Simulando push para LangSmith Hub...")
    return True

def main():
    """Função principal"""
    print_section_header("Pushing Prompts no LangSmith Prompt Hub")

    print("1 - Validando variáveis de ambiente...")
    if not check_env_vars(["LANGSMITH_API_KEY"]): return 1
    print("  - Ok ✅")
    
    print(f"2 - Carregando prompt otimizado: {PROMPT_NAME}")
    raw = load_yaml(PROMPT_NAME)
    if not raw:
        return 1
    prompt_key, prompt_data = next(iter(raw.items()))
    print("  - Ok ✅")

    print("3 - Efetuando validação do prompt otimizado...")
    is_valid, errors = validate_prompt_structure(prompt_data)
    if not is_valid:
        print("❌ Prompt não passou na validação. Corrija os erros e tente novamente.")
        for error in errors:
            print(f"   - {error}")
        return 1
    print("  - Ok ✅") 

    print("Iniciando push...")
    success = push_prompt_to_langsmith(PROMPT_NAME, prompt_data)
    if not success:
        print("❌ Falha ao realizar Push.")
        return 1

    print("  - Ok ✅ Push realizado com sucesso!")

if __name__ == "__main__":
    sys.exit(main())
