"""
Testes automatizados para validação de prompts.

Os testes são parametrizados sobre os prompts otimizados em `prompts/`,
excluindo o baseline `*_v1.yml` (que existe apenas para comparação e não aplica
as técnicas avançadas exigidas pelas verificações de qualidade).
"""
import re
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
OPTIMIZED_PROMPTS = sorted(
    p for p in PROMPTS_DIR.glob("*.yml") if "_v1" not in p.name
)


def load_prompt(file_path: Path) -> dict:
    """Carrega o YAML e retorna o dict interno do prompt (1 nível abaixo)."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return next(iter(data.values()))


@pytest.fixture(params=OPTIMIZED_PROMPTS, ids=[p.stem for p in OPTIMIZED_PROMPTS])
def prompt_data(request):
    return load_prompt(request.param)


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt_data):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert 'system_prompt' in prompt_data, "Campo 'system_prompt' ausente no YAML"
        assert prompt_data['system_prompt'].strip(), "Campo 'system_prompt' está vazio"

    def test_prompt_has_role_definition(self, prompt_data):
        """Verifica se o prompt define uma persona (ex: 'Você é um especialista...')."""
        sp = prompt_data['system_prompt']
        assert re.search(r'\bVocê é (um|uma)\b', sp), (
            "Prompt deve definir uma persona iniciando com 'Você é um/uma ...'"
        )

    def test_prompt_mentions_format(self, prompt_data):
        """Verifica se o prompt exige formato Markdown ou User Story padrão (BDD)."""
        sp = prompt_data['system_prompt'].lower()
        format_markers = [
            'user story',
            'como um ',                # template padrão de user story
            'critérios de aceitação',
            'dado que',                # BDD
            'markdown',
        ]
        found = [m for m in format_markers if m in sp]
        assert found, (
            "Prompt deve mencionar formato de saída (User Story padrão, BDD ou Markdown). "
            f"Esperado encontrar pelo menos um de: {format_markers}"
        )

    def test_prompt_has_few_shot_examples(self, prompt_data):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        sp_lower = prompt_data['system_prompt'].lower()
        has_examples_section = 'exemplo' in sp_lower
        input_markers = ('relato:', 'input:', 'entrada:', 'bug report:', 'bug:')
        has_input_marker = any(m in sp_lower for m in input_markers)
        assert has_examples_section and has_input_marker, (
            "Prompt deve conter exemplos few-shot — palavra 'exemplo' + um marcador "
            f"de entrada ({input_markers})"
        )

    def test_prompt_no_todos(self, prompt_data):
        """Garante que não há marcadores pendentes ([TODO]/FIXME/etc.) no texto."""
        sp = prompt_data['system_prompt']
        todo_markers = ['[TODO]', 'TODO:', 'FIXME', 'XXX:', '<TODO>', '[FIXME]']
        present = [m for m in todo_markers if m in sp]
        assert not present, f"Prompt contém marcadores pendentes: {present}"

    def test_minimum_techniques(self, prompt_data):
        """Verifica (pelos metadados do YAML) se ao menos 2 técnicas foram listadas."""
        techniques = prompt_data.get('techniques_applied', [])
        assert isinstance(techniques, list), (
            f"'techniques_applied' deve ser uma lista, recebido: {type(techniques).__name__}"
        )
        assert len(techniques) >= 2, (
            f"Esperado >= 2 técnicas em 'techniques_applied', "
            f"encontrado {len(techniques)}: {techniques}"
        )

    def test_validate_prompt_structure(self, prompt_data):
        """Valida a estrutura completa do prompt via utils.validate_prompt_structure.

        Cobre, de uma só vez: campos obrigatórios (description, system_prompt,
        version), system_prompt não-vazio, ausência de 'TODO' e mínimo de 2
        técnicas declaradas.
        """
        is_valid, errors = validate_prompt_structure(prompt_data)
        assert is_valid, f"validate_prompt_structure falhou: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
