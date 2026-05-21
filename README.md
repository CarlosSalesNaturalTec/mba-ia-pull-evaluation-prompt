# mba-ia-pull-evaluation-prompt

Projeto de estudo do MBA em IA focado em **engenharia de prompts** com versionamento via **LangSmith Hub**. O repositório contém scripts para fazer *pull* e *push* de prompts no Hub, além de um pipeline de avaliação que mede a qualidade das versões de cada prompt sobre datasets de referência.

O caso de uso central é a transformação de **relatos de bug** (linguagem natural escrita por usuários finais) em **user stories** estruturadas e prontas para serem consumidas por times de desenvolvimento.

---

## Estrutura do repositório

```
.
├── prompts/
│   ├── bug_to_user_story_v1.yml   # versão baseline (sem técnicas avançadas)
│   └── bug_to_user_story_v2.yml   # versão evoluída com CoT, Few-Shot e Edge-Case Handling
├── datasets/
│   └── bug_to_user_story.jsonl    # dataset de avaliação (entrada -> referência)
├── src/
│   ├── pull_prompts.py            # baixa prompts do LangSmith Hub
│   ├── push_prompts.py            # envia prompts versionados para o Hub
│   ├── evaluate.py                # executa avaliações sobre o dataset
│   ├── metrics.py                 # métricas de qualidade
│   └── utils.py
└── tests/
    └── test_prompts.py
```

---

## O prompt `bug_to_user_story_v2.yml`

A versão **v2** evolui o prompt baseline (v1, que apenas pedia "crie uma user story a partir do relato") e aplica três técnicas combinadas de engenharia de prompts. O objetivo é tornar a geração das user stories **mais consistente, mais segura e mais fiel ao relato original**.

### Técnicas aplicadas

O arquivo declara explicitamente no campo `techniques_applied`:

```yaml
techniques_applied:
  - chain-of-thought
  - few-shot
  - edge-case-handling
```

A seguir, o **o quê** e o **porquê** de cada uma.

---

### 1. Chain of Thought (CoT)

**O que é**
Técnica que instrui o modelo a **raciocinar passo a passo** antes de produzir a resposta final, em vez de saltar direto para a saída. No `system_prompt`, isso aparece como uma sequência numerada (Passo 1 a Passo 5) cobrindo:

1. Compreensão do bug (funcionalidade, comportamento atual, comportamento esperado).
2. Identificação do impacto e do tipo de usuário afetado.
3. Definição do valor de negócio.
4. Critérios de aceitação verificáveis.
5. Geração da user story final.

**Por que foi aplicada**

- **Qualidade superior em tarefas de análise.** A transformação bug → user story exige inferência (identificar tipo de usuário, valor de negócio, critérios), e CoT é o mecanismo mais estabelecido para forçar o modelo a executar essa inferência de forma estruturada.
- **Redução de respostas superficiais.** Sem CoT, o modelo tende a produzir user stories genéricas que apenas reescrevem o relato. Com os passos explícitos, cada user story passa a refletir uma análise de impacto e de valor.
- **Auditabilidade.** O raciocínio explícito permite que o avaliador (humano ou automático em `src/evaluate.py`) inspecione *onde* a geração falhou — comportamento atual mal interpretado? Impacto subestimado? — em vez de só julgar o resultado final.
- **Consistência entre execuções.** Padronizar os passos reduz a variância entre chamadas e facilita comparar versões do prompt no pipeline de avaliação.

---

### 2. Few-Shot Prompting

**O que é**
Técnica que fornece **exemplos completos de entrada e saída** dentro do próprio prompt, ensinando o modelo por demonstração. No `system_prompt` da v2, dois exemplos completos são apresentados (login falhando e upload de foto), cada um já contendo:

- O relato de bug original.
- O raciocínio estruturado (resultado dos Passos 1–4).
- Os critérios de aceitação.
- A user story final.

**Por que foi aplicada**

- **Ancoragem do formato de saída.** Mesmo com CoT, modelos podem variar tom, granularidade e estrutura entre execuções. Os exemplos servem como "template vivo" e fixam o estilo esperado.
- **Calibração da qualidade.** Os exemplos definem o padrão de qualidade aceitável — nível de detalhe nos critérios de aceitação, profundidade do parágrafo complementar, vocabulário. Sem eles, "user story" é um conceito ambíguo o suficiente para gerar saídas em escalas muito diferentes.
- **Sinergia com o CoT.** Few-shot mostra o CoT *aplicado*; juntos transformam uma instrução abstrata ("raciocine passo a passo") em um padrão concreto e replicável.
- **Reuso dos exemplos do baseline.** Os mesmos relatos da v1 são reaproveitados, o que mantém a comparabilidade entre v1 e v2 nas métricas de avaliação.

---

### 3. Edge-Case Handling (Validação prévia)

**O que é**
Técnica que define **explicitamente** como o modelo deve se comportar diante de entradas atípicas, ambíguas ou maliciosas — em vez de deixar essas situações ao acaso. No `system_prompt` da v2, isso aparece como o **Passo 0**, executado antes do Passo 1, cobrindo 8 cenários:

| Cenário | Comportamento esperado |
|---|---|
| a) Relato vazio/insuficiente | Recusa estruturada pedindo as 3 informações mínimas |
| b) Múltiplos bugs no mesmo relato | Gera uma user story por bug, numeradas |
| c) Solicitação de feature (não é bug) | Recusa e orienta a reformular |
| d) Dados sensíveis (senha, CPF, token) | Sanitização com `[REDACTED]` e prossegue |
| e) Off-topic / prompt injection | Recusa de escopo |
| f) Ambiguidade crítica | Prossegue marcando "Suposição a validar" |
| g) Idioma diferente do PT-BR | Traduz internamente e indica no raciocínio |
| h) Regra de ouro | Nunca inventar sintomas ausentes no relato |

**Por que foi aplicada**

- **Robustez do prompt em produção.** Datasets reais (e relatos reais de usuários) contêm entradas degeneradas: relatos curtos demais, descrições com múltiplos problemas misturados, pedidos que não são bugs. Sem tratamento explícito, o modelo "inventa" para preencher os campos do template — o que polui as métricas e gera user stories enganosas.
- **Segurança e privacidade.** O item (d) impede que dados sensíveis vazem do relato para a user story (que será lida por desenvolvedores, salva em sistemas de tickets, indexada). O item (e) protege contra tentativas de prompt injection embutidas no relato.
- **Fidelidade ao relato (item h).** A "regra de ouro" combate o principal modo de falha desse tipo de prompt: o modelo confabular sintomas, navegadores, telas e mensagens de erro que **nunca estiveram no input**. Isso é especialmente importante para a métrica de **groundedness** medida em `src/metrics.py`.
- **Posicionamento intencional.** O Passo 0 vem **antes** do Passo 1: se o relato cair em um caso de parada (a, c, e), o modelo aborta sem gastar raciocínio nos passos seguintes, o que reduz custo de tokens e elimina a chance de a saída "padrão" ser produzida em cima de uma entrada inválida.

---

## Como as técnicas se complementam

As três técnicas atacam dimensões distintas da qualidade do prompt e por isso são combinadas:

| Técnica | Dimensão de qualidade atacada |
|---|---|
| Chain of Thought | **Profundidade** do raciocínio (a user story reflete análise, não cópia) |
| Few-Shot | **Forma** e **calibração** (padroniza estilo, estrutura e nível de detalhe) |
| Edge-Case Handling | **Robustez** e **segurança** (mantém qualidade fora do caminho feliz) |

A v2 é, portanto, uma evolução em três frentes simultâneas em relação à v1, e cada técnica pode ser isolada nos experimentos de avaliação para medir sua contribuição marginal.
