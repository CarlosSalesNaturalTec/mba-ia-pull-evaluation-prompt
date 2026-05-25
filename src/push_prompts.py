"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

SIMPLIFICADO: Código mais limpo e direto ao ponto.
"""

import truststore               # Garantir que certificados SSL do LangSmith sejam confiáveis.  O truststore faz o Python usar os certificados do repositório de certificados do Windows, incluindo o certificado raiz do proxy corporativo que já está instalado pelo TI.
truststore.inject_into_ssl()    # Necessário para evitar erros de SSL ao conectar com o LangSmith Hub. 

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
        prompt_name: Identificador no Hub (ex.: "bug_to_user_story_v2" ou "owner/bug_to_user_story_v2")
        prompt_data: Dados do prompt (system_prompt, user_prompt, description, tags, ...)

    Returns:
        True se sucesso, False caso contrário
    """
    try:
        client = Client()

        template = ChatPromptTemplate.from_messages([
            ("system", prompt_data["system_prompt"]),
            ("human", prompt_data["user_prompt"]),
        ])

        tags = list(prompt_data.get("tags") or [])
        techniques = prompt_data.get("techniques_applied") or []
        readme = (
            f"Técnicas aplicadas: {', '.join(techniques)}" if techniques else None
        )

        url = client.push_prompt(
            prompt_name,
            object=template,
            description=prompt_data.get("description") or "",
            tags=tags,
            readme=readme,
            is_public=True,
        )
        print(f"   URL: {url}")
        return True
    except Exception as e:
        print(f"   ❌ Erro no push: {e}")
        return False
    

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

    print("4 - Iniciando push...")
    success = push_prompt_to_langsmith(prompt_key, prompt_data)
    if not success: return 1

    print("  - Ok ✅ Push realizado com sucesso!")

if __name__ == "__main__":
    sys.exit(main())
