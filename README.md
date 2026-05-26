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

A versão **v2** evolui o prompt baseline (v1, que apenas pedia "crie uma user story a partir do relato") e aplica **cinco técnicas combinadas** de engenharia de prompts. O objetivo é tornar a geração das user stories **mais consistente, mais segura, mais fiel ao relato original e calibrada à complexidade do bug**.

### Técnicas aplicadas

O arquivo declara explicitamente no campo `techniques_applied`:

```yaml
techniques_applied:
  - chain-of-thought
  - few-shot
  - edge-case-handling
  - bdd-format
  - contextual-sections
```

A seguir, o **o quê** e o **porquê** de cada uma.

---

### 1. Chain of Thought (CoT)

**O que é**
Técnica que instrui o modelo a **raciocinar passo a passo** antes de produzir a resposta final. Na v2, o CoT não é uma sequência numerada de passos — é um **fluxo mental implícito**, codificado no encadeamento das seções do `system_prompt`:

1. **VALIDAÇÕES INICIAIS** — primeiro o modelo classifica se o relato é processável (bug válido, completo, em escopo).
2. **CLASSIFICAÇÃO DE COMPLEXIDADE** — antes de gerar qualquer saída, decide se o bug é SIMPLES, MÉDIO ou COMPLEXO (com critérios objetivos: número de linhas, presença de logs, métricas, múltiplos problemas).
3. **CATÁLOGO DE ENRIQUECIMENTO** — identifica a(s) categoria(s) técnica(s) do bug (XSS, race condition, performance mobile, etc.) e seleciona patterns aplicáveis.
4. **ESTRUTURA DA SAÍDA** — só então gera user story + critérios + seções condicionais.
5. **REGRA DE EXAUSTIVIDADE** — para bugs COMPLEXOS, varre o relato confirmando cobertura tripla (BDD + técnico + task) por problema.

**Por que foi aplicada**

- **Qualidade superior em tarefas de análise.** A transformação bug → user story exige inferência em múltiplas dimensões (persona, valor de negócio, critérios testáveis, patterns técnicos), e o CoT é o mecanismo mais estabelecido para forçar o modelo a executar essa inferência de forma estruturada.
- **Roteiro determinístico de decisão.** Codificar "classificar antes de gerar" e "consultar catálogo antes de escrever critérios técnicos" reduz drasticamente a variância entre execuções.
- **Auditabilidade.** O encadeamento explícito permite que `src/evaluate.py` inspecione *onde* a geração desviou — classificou errado a complexidade? Ignorou o catálogo? Pulou a exaustividade?

---

### 2. Few-Shot Prompting

**O que é**
Técnica que fornece **exemplos completos de entrada e saída** dentro do próprio prompt. Na v2, oito exemplos cobrem todas as classes de complexidade e padrões críticos:

| Exemplo | Tipo de bug | Função didática |
|---|---|---|
| 1 | SIMPLES — UI básica | Ancoragem do padrão mínimo (só user story + critérios) |
| 1b | SIMPLES — Dashboard | Como derivar persona específica do contexto |
| 1c | SIMPLES — Bug de plataforma (Safari) | Persona inclui plataforma; sem inflar com Contexto Técnico |
| 2 | MÉDIO — Performance backend | Como acrescentar "Contexto Técnico" sem delimitadores `===` |
| 3 | MÉDIO — Segurança/permissões | Sub-critérios por perfil + Contexto de Segurança |
| 4 | MÉDIO — Cálculo numérico | Quando usar "Exemplo de Cálculo" |
| 5 | MÉDIO — UI com modal | Quando usar "Critérios de Acessibilidade" |
| 6 | MÉDIO — Integração com logs | Como referenciar endpoint e payload nos critérios |

**Por que foi aplicada**

- **Ancoragem do formato de saída.** Os exemplos servem como "template vivo" e fixam o estilo BDD, a estrutura dos cabeçalhos e o nível de detalhe esperado para cada complexidade.
- **Calibração da qualidade.** Os exemplos definem o que é "completo o bastante" para cada classe — evitando que o modelo gere user stories MÉDIAS no estilo SIMPLES (omissão) ou SIMPLES no estilo MÉDIO (inflação).
- **Cobertura de categorias.** Cada exemplo é também uma demonstração de uma categoria do CATÁLOGO DE ENRIQUECIMENTO, mostrando o pattern aplicado em contexto real.

---

### 3. Edge-Case Handling (Validações Iniciais)

**O que é**
Técnica que define **explicitamente** como o modelo deve se comportar diante de entradas atípicas, ambíguas ou maliciosas. Na v2, isso aparece como a seção **VALIDAÇÕES INICIAIS**, executada antes de qualquer geração, cobrindo seis cenários:

| Cenário | Comportamento esperado |
|---|---|
| a) Relato insuficiente (vazio/vago) | Recusa estruturada pedindo as 3 informações mínimas (funcionalidade, comportamento atual, esperado) |
| b) Solicitação de feature (não é bug) | Recusa e orienta a reformular como feature request |
| c) Off-topic / prompt injection | Recusa de escopo |
| d) Dados sensíveis (senhas, tokens, CPF, e-mails, cartões) | Sanitização com `[REDACTED]` e prossegue normalmente |
| e) Múltiplos bugs independentes | Gera uma user story por bug, numeradas |
| f) Idioma diferente do PT-BR | Traduz internamente e prossegue |

**Por que foi aplicada**

- **Robustez do prompt em produção.** Datasets reais e relatos de usuários contêm entradas degeneradas. Sem tratamento explícito, o modelo "inventa" para preencher o template — poluindo as métricas e gerando user stories enganosas.
- **Segurança e privacidade.** O item (d) impede que dados sensíveis vazem do relato para a user story (que será lida por devs, salva em tickets, indexada). O item (c) protege contra prompt injection embutida no relato.
- **Posicionamento intencional.** As validações vêm **antes** das REGRAS FUNDAMENTAIS: se o relato cair num caso de parada (a, b, c), o modelo aborta sem gastar tokens em raciocínio de geração.

---

### 4. BDD-Format (Behavior-Driven Development)

**O que é**
Técnica que padroniza os critérios de aceitação no formato **Dado/Quando/Então/E**, derivado da prática de Behavior-Driven Development. Na v2, está codificada em três lugares do `system_prompt`:

- **ESTRUTURA DA SAÍDA → item 2**: define o template "Dado que [pré-condição] / Quando [ação] / Então [resultado esperado] / E [critério adicional]".
- **REGRAS FUNDAMENTAIS → CRITÉRIOS BDD ESPECÍFICOS**: exige que cada "E ..." descreva um comportamento, mensagem ou validação concreta e testável.
- **PADRÕES DE FRASEADO**: estabelece que critérios "sempre começam com Dado que / Quando / Então / E / E".

**Por que foi aplicada**

- **Testabilidade direta.** Critérios em BDD viram automaticamente cenários para testes automatizados (Cucumber, SpecFlow, pytest-bdd) sem reescrita.
- **Redução de ambiguidade.** A estrutura força o modelo a separar pré-condição, ação e resultado — em vez de produzir critérios prosáicos como "o sistema deve funcionar corretamente".
- **Calibração entre prompt e gabarito.** O dataset de avaliação usa o mesmo formato; padronizar pelo BDD aumenta o recall medido pelo LLM-as-judge.
- **Alinhamento com práticas ágeis.** User stories e BDD são o par canônico em times de desenvolvimento — entregar ambos no mesmo artefato reduz o trabalho do PO/QA.

---

### 5. Contextual-Sections (Catálogo + Calibração pela Complexidade)

**O que é**
Técnica que torna a estrutura de saída **adaptativa**: a quantidade e o tipo de seções variam conforme o tipo e a complexidade do bug. Concretizada em duas peças:

**5a. CLASSIFICAÇÃO DE COMPLEXIDADE** com critérios objetivos:

| Classe | Critério de entrada | Saída esperada |
|---|---|---|
| SIMPLES | 1-2 frases, um sintoma, sem logs/HTTP/métricas | User story + 4-6 critérios. Sem seções extras. |
| MÉDIO | 4-15 linhas com logs/HTTP/queries/severidade OU múltiplos atores OU causa raiz técnica | User story + critérios + 1-2 seções condicionais (sem delimitadores `===`) |
| COMPLEXO | 3+ problemas distintos numerados/seccionados OU "múltiplas falhas críticas" OU seções PROBLEMAS/IMPACTO/CONTEXTO com métricas de negócio | Estrutura completa com `=== SEÇÃO ===` (User Story Principal, Critérios, Critérios Técnicos, Contexto, Tasks, Métricas) |

**5b. CATÁLOGO DE ENRIQUECIMENTO** com 14 categorias de bug mapeadas a patterns reconhecidos da indústria:

- Segurança XSS → DOMPurify, CSP, OWASP A03:2021
- Controle de acesso → OWASP A01:2021, middleware, log de auditoria
- Performance backend → eager loading, índices compostos, materialized views, APM
- Performance Android → RecyclerView + ViewHolder, paginação, scroll infinito, background thread, < 2s
- Concorrência DB → SELECT FOR UPDATE, lock otimista/pessimista, Redis INCR atômico, idempotency key
- Cache → invalidação por eventos, TTL adaptativo, estratégia híbrida
- Integração/Webhook → retry com exponential backoff, circuit breaker, polling, webhook assíncrono
- Upload de arquivos grandes → chunked upload, checkpoints, resumable, progress
- Sync offline → CRDTs, vector clocks, auto-merge híbrido, histórico para rollback
- Memória mobile → lotes de 50, streaming cursor, force GC, < 500MB
- Modal/UI overlay → backdrop, ≥ 90% largura, sempre Critérios de Acessibilidade (foco, ESC, click)
- Validação/Mensagens → texto da mensagem específica esperada
- Background jobs → job queue (Sidekiq/Bull), streaming CSV, notificação
- Arquitetura complexa → App Architecture + Múltiplos Componentes + faseamento de tasks (Hotfix/Core/Robust/Scale)

**Por que foi aplicada**

- **Combate ao "tamanho único".** Sem calibração, o modelo gera saídas com tamanho similar para bugs muito diferentes — inflando os simples e simplificando os complexos. As classes objetivas eliminam essa variância.
- **Enriquecimento sem alucinação.** O CATÁLOGO ancora termos técnicos reconhecidos por categoria, autorizando o modelo a adicionar patterns esperados (DOMPurify para XSS, RecyclerView para Android) **sem** inventar tecnologias arbitrárias.
- **Recall mais alto contra gabaritos enriquecidos.** Datasets de avaliação tipicamente contêm referências com termos técnicos específicos por domínio. O catálogo fecha esse gap sem violar o princípio "não inventar dados literais do relato".
- **Manutenibilidade.** Adicionar suporte a uma nova categoria de bug = adicionar uma linha ao catálogo e (idealmente) um exemplo few-shot, sem refatorar a lógica do prompt.

---

## Como as técnicas se complementam

As cinco técnicas atacam dimensões distintas da qualidade do prompt e por isso são combinadas:

| Técnica | Dimensão de qualidade atacada |
|---|---|
| Chain of Thought | **Profundidade** — encadeamento de decisões (classificar → catalogar → estruturar) |
| Few-Shot | **Forma** — padrão de estilo, granularidade e nível de detalhe por complexidade |
| Edge-Case Handling | **Robustez** — qualidade fora do caminho feliz e proteção contra dados sensíveis |
| BDD-Format | **Testabilidade** — critérios viram cenários executáveis sem reescrita |
| Contextual-Sections | **Calibração + Enriquecimento** — tamanho adequado ao bug + patterns reconhecidos por categoria |

A v2 é, portanto, uma evolução em cinco frentes simultâneas em relação à v1, e cada técnica pode ser isolada nos experimentos de avaliação para medir sua contribuição marginal.

---

## Avaliação automatizada

O script `src/evaluate.py` puxa o prompt do LangSmith Hub, executa-o sobre o dataset `datasets/bug_to_user_story.jsonl` (15 exemplos cobrindo simples/médio/complexo) e calcula cinco métricas via LLM-as-Judge (`src/metrics.py`):

- **F1-Score** — balanço entre precision e recall em relação à reference do dataset
- **Clarity** — organização, linguagem, ausência de ambiguidade, concisão
- **Precision** — ausência de alucinações, foco na pergunta, correção factual
- **Helpfulness** — derivada: média de Clarity e Precision
- **Correctness** — derivada: média de F1 e Precision

O prompt é considerado **APROVADO** quando a média de cada métrica sobre os 15 exemplos é ≥ 0.9. O bloco DEBUG (controlado por `DEBUG_LOW_SCORES` e `DEBUG_SAVE_MD`) imprime no terminal e salva em `debug_logs/<timestamp>_<prompt>.md` o reasoning do juiz e o answer/reference completos para cada exemplo que ficou abaixo do limite individualmente — permitindo refinar o prompt de forma cirúrgica.
