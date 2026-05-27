"""
Script para criar EXPERIMENTOS no LangSmith usando juízes do Prompt Hub.

Diferente de evaluate.py (que faz um loop manual e imprime métricas no
terminal), este script usa `client.evaluate(...)` para registrar um
experimento formal no LangSmith — visível na aba "Experiments" do dataset,
comparável lado a lado com outros experimentos.

Fluxo:
1. Puxa do Hub o prompt sob teste (USERNAME/bug_to_user_story_v2)
2. Puxa do Hub os 3 juízes (judge_f1_score, judge_clarity, judge_precision)
   publicados via src/push_judges.py
3. Constrói uma função alvo (prompt | LLM) que produz a resposta a avaliar
4. Constrói 3 evaluators (LangSmith run evaluators) que invocam cada juiz
5. Dispara client.evaluate(...) sobre o dataset de avaliação
6. Imprime o link do experimento no terminal

Pré-requisitos:
- python src/push_prompts.py   (sobe o prompt v2)
- python src/push_judges.py    (sobe os 3 juízes)
"""

import truststore               # Garantir que certificados SSL do LangSmith sejam confiáveis.
truststore.inject_into_ssl()    # Necessário para evitar erros de SSL ao conectar com o LangSmith Hub.

import os
import sys
from typing import Any, Dict
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from langchain import hub
from utils import (
    check_env_vars,
    print_section_header,
    get_llm,
    get_eval_llm,
    extract_json_from_response,
)

load_dotenv()


PROMPT_UNDER_TEST = "bug_to_user_story_v1"
JUDGES = ["judge_f1_score", "judge_clarity", "judge_precision"]
DATASET_JSONL = "datasets/bug_to_user_story.jsonl"


def _input_text(example_inputs: Dict[str, Any]) -> str:
    """Extrai o texto de entrada dos diferentes formatos possíveis."""
    if not isinstance(example_inputs, dict):
        return ""
    return example_inputs.get("bug_report") or example_inputs.get("question") or ""


def _reference_text(example_outputs: Dict[str, Any]) -> str:
    if not isinstance(example_outputs, dict):
        return ""
    return example_outputs.get("reference", "")


def _answer_text(run_outputs: Any) -> str:
    """Extrai o conteúdo de texto da saída de um run do LangChain."""
    if run_outputs is None:
        return ""
    if isinstance(run_outputs, dict):
        if "output" in run_outputs and hasattr(run_outputs["output"], "content"):
            return run_outputs["output"].content
        if "content" in run_outputs:
            return run_outputs["content"]
        if "output" in run_outputs and isinstance(run_outputs["output"], str):
            return run_outputs["output"]
    return str(run_outputs)


def build_target():
    """Monta a função alvo: prompt sob teste encadeado com o LLM principal."""
    username = os.getenv("USERNAME_LANGSMITH_HUB")
    prompt = hub.pull(f"{username}/{PROMPT_UNDER_TEST}")
    llm = get_llm(temperature=0)
    chain = prompt | llm

    def target(inputs: Dict[str, Any]) -> Dict[str, Any]:
        response = chain.invoke(inputs)
        content = response.content if hasattr(response, "content") else str(response)
        return {"output": content}

    return target


def build_evaluator(name: str, judge_prompt, score_fn):
    """
    Constrói um run-evaluator que invoca o juiz puxado do Hub
    e converte sua resposta JSON em um score numérico.
    """
    eval_llm = get_eval_llm(temperature=0)

    def _evaluator(run, example) -> Dict[str, Any]:
        question = _input_text(getattr(example, "inputs", {}) or {})
        reference = _reference_text(getattr(example, "outputs", {}) or {})
        answer = _answer_text(getattr(run, "outputs", {}) or {})

        messages = judge_prompt.format_messages(
            question=question,
            answer=answer,
            reference=reference,
        )
        response = eval_llm.invoke(messages)
        parsed = extract_json_from_response(response.content) or {}

        try:
            score = float(score_fn(parsed))
        except (TypeError, ValueError, KeyError, ZeroDivisionError):
            score = 0.0

        return {
            "key": name,
            "score": round(score, 4),
            "comment": str(parsed.get("reasoning", ""))[:1000],
        }

    return _evaluator


def f1_from_precision_recall(parsed: Dict[str, Any]) -> float:
    p = float(parsed.get("precision", 0.0))
    r = float(parsed.get("recall", 0.0))
    if (p + r) <= 0:
        return 0.0
    return 2 * p * r / (p + r)


def score_direct(parsed: Dict[str, Any]) -> float:
    return float(parsed.get("score", 0.0))


def ensure_dataset(client: Client, dataset_name: str, jsonl_path: str) -> str:
    """Cria o dataset a partir do JSONL caso ainda não exista no LangSmith."""
    import json

    existing = next((ds for ds in client.list_datasets(dataset_name=dataset_name) if ds.name == dataset_name), None)
    if existing:
        print(f"   ✓ Dataset '{dataset_name}' já existe")
        return dataset_name

    if not Path(jsonl_path).exists():
        raise FileNotFoundError(f"Arquivo de dataset não encontrado: {jsonl_path}")

    dataset = client.create_dataset(dataset_name=dataset_name)
    count = 0
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            example = json.loads(line)
            client.create_example(
                dataset_id=dataset.id,
                inputs=example["inputs"],
                outputs=example["outputs"],
            )
            count += 1
    print(f"   ✓ Dataset criado com {count} exemplos")
    return dataset_name


def main():
    print_section_header("EXPERIMENTO NO LANGSMITH (LLM-as-Judge via Hub)")

    provider = os.getenv("LLM_PROVIDER", "openai")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    eval_model = os.getenv("EVAL_MODEL", "gpt-4o")
    print(f"Provider:           {provider}")
    print(f"Modelo principal:   {llm_model}")
    print(f"Modelo de avaliação:{eval_model}")

    required = ["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB", "LLM_PROVIDER"]
    if provider == "openai":
        required.append("OPENAI_API_KEY")
    elif provider in ("google", "gemini"):
        required.append("GOOGLE_API_KEY")
    if not check_env_vars(required):
        return 1

    username = os.getenv("USERNAME_LANGSMITH_HUB")
    project_name = os.getenv("LANGSMITH_PROJECT", "prompt-optimization-challenge-resolved")
    dataset_name = f"{project_name}-eval"

    client = Client()

    print("\n1 - Garantindo dataset no LangSmith...")
    ensure_dataset(client, dataset_name, DATASET_JSONL)

    print("\n2 - Puxando juízes do Hub...")
    judges = {}
    for judge_slug in JUDGES:
        full_name = f"{username}/{judge_slug}"
        print(f"   → {full_name}")
        judges[judge_slug] = hub.pull(full_name)

    print("\n3 - Montando função alvo (prompt sob teste)...")
    target = build_target()

    print("\n4 - Construindo evaluators a partir dos juízes...")
    evaluators = [
        build_evaluator("f1_score", judges["judge_f1_score"], f1_from_precision_recall),
        build_evaluator("clarity",  judges["judge_clarity"],  score_direct),
        build_evaluator("precision", judges["judge_precision"], score_direct),
    ]

    print("\n5 - Disparando experimento (client.evaluate)...")
    results = client.evaluate(
        target,
        data=dataset_name,
        evaluators=evaluators,
        experiment_prefix=PROMPT_UNDER_TEST,
        metadata={
            "prompt_under_test": f"{username}/{PROMPT_UNDER_TEST}",
            "llm_model": llm_model,
            "eval_model": eval_model,
            "provider": provider,
            "judges": [f"{username}/{j}" for j in JUDGES],
        },
    )

    experiment_name = getattr(results, "experiment_name", None) or "experiment"
    print(f"\n✅ Experimento criado: {experiment_name}")
    print("\nAcesse o dashboard:")
    print(f"   https://smith.langchain.com/datasets")
    print(f"   (procure pelo dataset '{dataset_name}' → aba Experiments)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
