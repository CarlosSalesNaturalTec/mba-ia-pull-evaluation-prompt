"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do template + metadados do recurso Prompt
3. Extrai system_prompt, user_prompt, description, version, created_at, tags
4. Salva localmente em prompts/bug_to_user_story_v1.yml
"""

import sys
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts.chat import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

PROMPT_NAME = "leonanluppi/bug_to_user_story_v1"
OUTPUT_PATH = "prompts/bug_to_user_story_v1.yml"

def extract_prompt_fields(client: Client, prompt_name: str) -> dict:
    """Combina pull_prompt + get_prompt para montar o dict no formato alvo."""
    template = client.pull_prompt(prompt_name)
    meta = client.get_prompt(prompt_name)

    system_prompt, user_prompt = None, None
    for msg in template.messages:
        if isinstance(msg, SystemMessagePromptTemplate):
            system_prompt = msg.prompt.template
        elif isinstance(msg, HumanMessagePromptTemplate):
            user_prompt = msg.prompt.template

    commit_hash = getattr(meta, "last_commit_hash", "") or ""
    created_at = getattr(meta, "created_at", None)
    tags = getattr(meta, "tags", None) or list(template.tags or [])

    key = getattr(meta, "repo_handle", None) or prompt_name.split("/")[-1]
    return {
        key: {
            "description": getattr(meta, "description", None),
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "version": commit_hash[:8] if commit_hash else None,
            "created_at": created_at.isoformat() if created_at else None,
            "tags": list(tags),
        }
    }


def pull_prompts_from_langsmith():
    try:
        print("Baixando prompt...")
        client = Client()
        data = extract_prompt_fields(client, PROMPT_NAME)
        print("✅ Prompt baixado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao efetuar o pull do prompt: {e}")
        return

    print("Salvando prompt...")
    if save_yaml(data, OUTPUT_PATH):
        print(f"✅ Prompt salvo em {OUTPUT_PATH}")


def main():
    """Função principal"""
    print_section_header("Pulling Prompts do LangSmith Prompt Hub")
    if check_env_vars(["LANGSMITH_API_KEY"]):
        pull_prompts_from_langsmith()


if __name__ == "__main__":
    sys.exit(main())
