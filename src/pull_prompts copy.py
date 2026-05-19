"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull dos prompts do Hub
3. Salva localmente em prompts/bug_to_user_story_v1.yml

SIMPLIFICADO: Usa serialização nativa do LangChain para extrair prompts.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain import hub
from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    AIMessagePromptTemplate,
)
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

_ROLE_BY_TYPE = {
    SystemMessagePromptTemplate: "system",
    HumanMessagePromptTemplate: "human",
    AIMessagePromptTemplate: "ai",
}


def serialize_prompt(prompt: ChatPromptTemplate) -> dict:
    """Converte ChatPromptTemplate em dict simples e legível para YAML."""
    messages = []
    for msg in prompt.messages:
        role = next(
            (r for cls, r in _ROLE_BY_TYPE.items() if isinstance(msg, cls)),
            msg.__class__.__name__,
        )
        messages.append({"role": role, "template": msg.prompt.template})

    data = {
        "name": (prompt.metadata or {}).get("lc_hub_repo"),
        "input_variables": list(prompt.input_variables),
        "metadata": dict(prompt.metadata) if prompt.metadata else {},
        "messages": messages,
    }
    return data

def pull_prompts_from_langsmith():
    try:
        print("Baixando prompt...")
        prompt = hub.pull("leonanluppi/bug_to_user_story_v1")
        print("✅ Prompt baixado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao efetuar o pull do prompt: {e}")
        return

    print("Salvando prompt...")
    if save_yaml(serialize_prompt(prompt), "prompts/bug_to_user_story_v1.yml"):
        print("✅ Prompt salvo com sucesso!")

def main():
    """Função principal"""
    print_section_header("Pulling Prompts do LangSmith Prompt Hub") 
    if check_env_vars(["LANGSMITH_API_KEY"]):
        pull_prompts_from_langsmith()

if __name__ == "__main__":
    sys.exit(main())
