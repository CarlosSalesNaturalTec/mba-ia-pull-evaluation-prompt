"""
Script para fazer push dos prompts de LLM-as-Judge ao LangSmith Prompt Hub.

Este script:
1. Define os 3 juízes existentes em metrics.py como ChatPromptTemplate
   (F1-Score, Clarity, Precision) com variáveis {question}, {answer} e {reference}
2. Faz push PÚBLICO ao LangSmith Hub
3. Adiciona metadados (description, tags, readme)

Após o push, os juízes podem ser consumidos via:
    judge = hub.pull(f"{USERNAME_LANGSMITH_HUB}/judge_f1_score")
"""

import truststore               # Garantir que certificados SSL do LangSmith sejam confiáveis.
truststore.inject_into_ssl()    # Necessário para evitar erros de SSL ao conectar com o LangSmith Hub.

import os
import sys
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate
from utils import check_env_vars, print_section_header

load_dotenv()


JUDGES = {
    "judge_f1_score": {
        "description": "Juiz LLM-as-Judge que calcula PRECISION e RECALL para derivar F1-Score de respostas geradas (bug → user story).",
        "tags": ["judge", "evaluator", "f1-score", "bug-to-user-story"],
        "readme": "Retorna JSON com 'precision', 'recall' e 'reasoning'. F1 = 2*P*R/(P+R) deve ser calculado pelo consumidor.",
        "system": (
            "Você é um avaliador especializado em medir a qualidade de respostas geradas por IA. "
            "Sua tarefa é calcular PRECISION e RECALL para determinar o F1-Score."
        ),
        "human": (
            "PERGUNTA DO USUÁRIO:\n{question}\n\n"
            "RESPOSTA ESPERADA (Ground Truth):\n{reference}\n\n"
            "RESPOSTA GERADA PELO MODELO:\n{answer}\n\n"
            "INSTRUÇÕES:\n\n"
            "1. PRECISION (0.0 a 1.0):\n"
            "   - Quantas informações na resposta gerada são CORRETAS e RELEVANTES?\n"
            "   - Penalizar informações incorretas, inventadas ou desnecessárias.\n"
            "   - 1.0 = todas informações são corretas e relevantes\n"
            "   - 0.0 = nenhuma informação é correta ou relevante\n\n"
            "2. RECALL (0.0 a 1.0):\n"
            "   - Quantas informações da resposta esperada estão PRESENTES na resposta gerada?\n"
            "   - Penalizar informações importantes que foram omitidas.\n"
            "   - 1.0 = todas informações importantes estão presentes\n"
            "   - 0.0 = nenhuma informação importante está presente\n\n"
            "3. RACIOCÍNIO:\n"
            "   - Explique brevemente sua avaliação, citando exemplos do que estava correto/incorreto.\n\n"
            "IMPORTANTE: Retorne APENAS um objeto JSON válido no formato:\n"
            "{{\n"
            '  "precision": <valor entre 0.0 e 1.0>,\n'
            '  "recall": <valor entre 0.0 e 1.0>,\n'
            '  "reasoning": "<sua explicação em até 100 palavras>"\n'
            "}}\n\n"
            "NÃO adicione nenhum texto antes ou depois do JSON."
        ),
    },
    "judge_clarity": {
        "description": "Juiz LLM-as-Judge que avalia CLAREZA da resposta (organização, linguagem, ausência de ambiguidade e concisão).",
        "tags": ["judge", "evaluator", "clarity", "bug-to-user-story"],
        "readme": "Retorna JSON com 'score' (média dos 4 critérios) e 'reasoning'.",
        "system": "Você é um avaliador especializado em medir a CLAREZA de respostas geradas por IA.",
        "human": (
            "PERGUNTA DO USUÁRIO:\n{question}\n\n"
            "RESPOSTA GERADA PELO MODELO:\n{answer}\n\n"
            "RESPOSTA ESPERADA (Referência):\n{reference}\n\n"
            "INSTRUÇÕES:\n\n"
            "Avalie a CLAREZA da resposta gerada com base nos critérios:\n\n"
            "1. ORGANIZAÇÃO (0.0 a 1.0):\n"
            "   - A resposta tem estrutura lógica e bem organizada?\n"
            "   - Informações estão em ordem sensata?\n\n"
            "2. LINGUAGEM (0.0 a 1.0):\n"
            "   - Usa linguagem simples e direta?\n"
            "   - Evita jargões desnecessários?\n"
            "   - Fácil de entender?\n\n"
            "3. AUSÊNCIA DE AMBIGUIDADE (0.0 a 1.0):\n"
            "   - A resposta é clara e sem ambiguidades?\n"
            "   - Não deixa dúvidas sobre o que está sendo comunicado?\n\n"
            "4. CONCISÃO (0.0 a 1.0):\n"
            "   - É concisa sem ser curta demais?\n"
            "   - Não tem informações redundantes?\n\n"
            "Calcule a MÉDIA dos 4 critérios para obter o score final.\n\n"
            "IMPORTANTE: Retorne APENAS um objeto JSON válido no formato:\n"
            "{{\n"
            '  "score": <valor entre 0.0 e 1.0>,\n'
            '  "reasoning": "<explicação detalhada da avaliação em até 100 palavras>"\n'
            "}}\n\n"
            "NÃO adicione nenhum texto antes ou depois do JSON."
        ),
    },
    "judge_precision": {
        "description": "Juiz LLM-as-Judge que avalia PRECISÃO (ausência de alucinações, foco e correção factual).",
        "tags": ["judge", "evaluator", "precision", "hallucination", "bug-to-user-story"],
        "readme": "Retorna JSON com 'score' (média dos 3 critérios) e 'reasoning'.",
        "system": "Você é um avaliador especializado em detectar PRECISÃO e ALUCINAÇÕES em respostas de IA.",
        "human": (
            "PERGUNTA DO USUÁRIO:\n{question}\n\n"
            "RESPOSTA GERADA PELO MODELO:\n{answer}\n\n"
            "RESPOSTA ESPERADA (Ground Truth):\n{reference}\n\n"
            "INSTRUÇÕES:\n\n"
            "Avalie a PRECISÃO da resposta gerada:\n\n"
            "1. AUSÊNCIA DE ALUCINAÇÕES (0.0 a 1.0):\n"
            "   - A resposta contém informações INVENTADAS ou não verificáveis?\n"
            "   - Todas as afirmações são baseadas em fatos?\n"
            "   - 1.0 = nenhuma alucinação detectada\n"
            "   - 0.0 = resposta cheia de informações inventadas\n\n"
            "2. FOCO NA PERGUNTA (0.0 a 1.0):\n"
            "   - A resposta responde EXATAMENTE o que foi perguntado?\n"
            "   - Não divaga ou adiciona informações não solicitadas?\n"
            "   - 1.0 = totalmente focada\n"
            "   - 0.0 = completamente fora do tópico\n\n"
            "3. CORREÇÃO FACTUAL (0.0 a 1.0):\n"
            "   - As informações estão CORRETAS quando comparadas com a referência?\n"
            "   - Não há erros ou imprecisões?\n"
            "   - 1.0 = todas informações corretas\n"
            "   - 0.0 = informações incorretas\n\n"
            "Calcule a MÉDIA dos 3 critérios para obter o score final.\n\n"
            "IMPORTANTE: Retorne APENAS um objeto JSON válido no formato:\n"
            "{{\n"
            '  "score": <valor entre 0.0 e 1.0>,\n'
            '  "reasoning": "<explicação detalhada em até 100 palavras, cite exemplos>"\n'
            "}}\n\n"
            "NÃO adicione nenhum texto antes ou depois do JSON."
        ),
    },
}


def push_judge_to_langsmith(client: Client, full_name: str, judge: dict) -> bool:
    """Faz push de um juiz para o LangSmith Hub (PÚBLICO)."""
    try:
        template = ChatPromptTemplate.from_messages([
            ("system", judge["system"]),
            ("human", judge["human"]),
        ])

        url = client.push_prompt(
            full_name,
            object=template,
            description=judge["description"],
            tags=judge["tags"],
            readme=judge.get("readme"),
            is_public=True,
        )
        print(f"   URL: {url}")
        return True
    except Exception as e:
        print(f"   ❌ Erro no push de '{full_name}': {e}")
        return False


def main():
    print_section_header("Pushing Judges no LangSmith Prompt Hub")

    print("1 - Validando variáveis de ambiente...")
    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1
    print("  - Ok ✅")

    username = os.getenv("USERNAME_LANGSMITH_HUB")
    client = Client()

    print(f"2 - Subindo {len(JUDGES)} juízes para o workspace '{username}'...")

    failures = 0
    for name, judge in JUDGES.items():
        full_name = f"{username}/{name}"
        print(f"\n→ {full_name}")
        if not push_judge_to_langsmith(client, full_name, judge):
            failures += 1

    print()
    if failures:
        print(f"⚠️  {failures}/{len(JUDGES)} juízes falharam no push.")
        return 1

    print(f"✅ {len(JUDGES)} juízes publicados com sucesso!")
    print("\nPróximo passo: rodar 'python src/run_experiment.py' para criar o experimento no LangSmith.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
