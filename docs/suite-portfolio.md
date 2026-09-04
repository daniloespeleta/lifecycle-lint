# A suíte: três repos, uma tese

## A tese

Jornada de cliente é artefato versionável. Se ela pode ser declarada em arquivo, ela pode ser lida, auditada e revisada em pull request, com histórico de versão e revisão por pares. Hoje ela vive dentro da interface da ferramenta de automação, onde não há diff entre versões nem registro de por que aquele delay é de 48 horas.

Os três repositórios cobrem três etapas do mesmo ciclo.

| Repo | Etapa | Certificação que ele exercita |
|---|---|---|
| `lifecycle-lint` | auditar | Claude Code in Action (Anthropic) |
| `segment-brief` | propor | Agents and Workflows (OpenAI Academy) |
| `lentes` | ler | AI Fluency: Framework & Foundations (Anthropic) |

Eles se encaixam em pipeline, e o encaixe é o que dá valor à suíte acima da soma das partes:

```
lentes            →  segment-brief        →  lifecycle-lint
prompts versionados  agente que propõe       linter que audita
e avaliados          jornada em YAML         antes do envio
```

A saída de um é a entrada do outro, o que torna objetivo o critério de aceite do agente: a jornada proposta precisa passar no linter. Isso resolve o problema mais difícil de portfólio com IA, que é evidenciar qualidade de output sem depender de julgamento subjetivo.

## Ordem de construção

**1. `lifecycle-lint` (pronto).** Primeiro porque um gestor de CRM reconhece o problema em poucos segundos, e porque ele sustenta os outros dois: sem o linter, o agente do projeto 2 fica sem critério de aceite.

**2. `segment-brief`.** Segundo pelo retorno em entrevista técnica. Vagas de CRM sênior perguntam sobre uso de IA, e a resposta usual se limita a geração de copy. Um agente com validação programática em cima muda o nível da conversa.

**3. `lentes`.** Terceiro porque é o de aparência mais fácil e demonstração mais difícil. Isolado, seria mais um repositório de prompts. Com harness de avaliação e integrado aos outros dois, vira infraestrutura de avaliação.

Estimativa: `segment-brief` em torno de quatro dias de trabalho concentrado, `lentes` em dois.

---

# Projeto 2: `segment-brief`

**Escopo em uma frase:** agente que lê uma tabela de eventos de produto e devolve o briefing de segmento com a jornada proposta em YAML, já validada pelo `lifecycle-lint`.

## O problema

A pergunta "que segmento deveríamos estar trabalhando" leva cerca de uma semana em quase toda operação. Alguém extrai dado, alguém cruza com receita, alguém escreve um documento, alguém contesta. O trabalho é repetitivo em quase toda a sua extensão, e a parte repetitiva é a delegável.

## Arquitetura

Roteador determinístico na entrada, agente no meio, validador na saída.

```
entrada: eventos.parquet + pergunta em linguagem natural
  │
  ├─ router (código, não modelo)
  │    classifica a pergunta em: exploração | diagnóstico | proposta
  │    e escolhe o conjunto de ferramentas permitido
  │
  ├─ agente (loop de tool use)
  │    tools:
  │      · run_sql(query)          → DuckDB sobre os eventos
  │      · cohort_sizes(filtros)   → tamanho e recorte, com piso de significância
  │      · rfm(janela)             → recência, frequência, valor
  │      · propose_journey(brief)  → gera YAML no formato canônico
  │
  └─ validador (código, não modelo)
       · o YAML gerado passa pelo lifecycle-lint
       · segmento abaixo do piso de amostra é rejeitado
       · em caso de falha, os achados voltam ao agente para uma segunda rodada
       · limite de duas rodadas, para conter custo de token em loop que não converge
```

## O que este projeto demonstra

O critério de quando usar agente e quando usar código. Roteamento e validação são determinísticos. O agente ocupa apenas a etapa em que a tarefa é aberta o bastante para justificar. Um agente que também roteia e valida a si mesmo não produz resultado auditável.

Demonstra também o loop fechado: a proposta é aceita ou rejeitada por um programa, com critério explícito.

## Dados

Dataset sintético de edtech, gerado por script versionado: 40 mil usuários, 18 meses de eventos (matrícula, login, aula assistida, pagamento, cancelamento), com sazonalidade e uma coorte de churn plantada para o agente encontrar. Dado sintético é requisito aqui, declarado no README. Base real de empregador não entra em portfólio público.

## Critério de pronto

- Três perguntas de exemplo rodando ponta a ponta, com transcrição do loop salva em `runs/`
- Toda jornada proposta passa no `lifecycle-lint` com `--fail-on error`
- Eval com dez perguntas e resposta esperada, rodando em CI
- Custo por execução medido e impresso ao fim do relatório
- README com a justificativa da separação entre roteador e agente

---

# Projeto 3: `lentes`

**Escopo em uma frase:** biblioteca de lentes de leitura para tarefas de CRM, versionadas, com harness que mede se elas continuam funcionando quando o prompt ou o modelo muda.

## O problema

Prompt é interface, com contrato de entrada e saída, e costuma ser tratado como texto solto: testado no chat, salvo em nota, esquecido. Quando o modelo é atualizado meses depois, a degradação passa despercebida por falta de linha de base.

## O que é uma lente

Uma lente é uma chave de leitura aplicada a um objeto de CRM. Cada uma é um arquivo com quatro partes, que correspondem às competências do framework de AI Fluency:

| Parte do arquivo | Competência | O que é na prática |
|---|---|---|
| `task` | Delegation | o que se delega ao modelo e o que fica com o humano |
| `prompt` | Description | a instrução, versionada, com histórico |
| `checks` | Discernment | asserções verificáveis sobre a saída |
| `provenance` | Diligence | modelo, data, revisor, e escopo de decisão da saída |

Lentes iniciais, todas derivadas de tarefa recorrente de operação:

1. **Nomear segmento**: recebe a definição técnica do filtro, devolve o nome de uso interno. Nomenclatura determina adoção do segmento pelo time.
2. **Diagnóstico de queda**: recebe série temporal de uma métrica de campanha, devolve hipóteses ordenadas por facilidade de teste.
3. **Copy por estágio**: recebe estágio de ciclo de vida e proposta de valor, devolve variações de assunto e primeira linha, com a hipótese que cada variação testa.
4. **Leitura de cancelamento**: recebe respostas abertas de pesquisa de churn, devolve eixos de motivo com contagem e citação de apoio, restrito às categorias presentes no texto.
5. **Auditoria de tom**: recebe uma régua completa e aponta onde o registro quebra entre mensagens.

## O harness

```bash
lentes eval nomear-segmento          # roda os casos, mostra o placar
lentes eval --all --model sonnet     # troca o modelo, compara com o anterior
lentes diff nomear-segmento v3 v4    # o que mudou entre as versões do prompt
```

Cada lente tem entre cinco e dez casos com asserção verificável. Boa parte das asserções é checagem de código: "não contém travessão", "devolve entre 3 e 5 itens", "não cita nome próprio ausente da entrada". As que exigem julgamento usam modelo como juiz, e o relatório marca quais são, porque juiz-modelo introduz viés que precisa ser visível na leitura do placar.

## Critério de pronto

- Cinco lentes com dez casos cada
- Placar de regressão em CI, com comparação contra a versão anterior
- Uma lente com histórico real de versão, mostrando o prompt v1 falhando em dois casos e o v3 passando
- README com o escopo que a biblioteca não cobre

---

## Nome de suíte

`journey-as-code` como guarda-chuva, se houver necessidade de um. É legível para avaliador técnico e enuncia a tese sem adjetivo.

O LEEA fica fora dos nomes de repositório. Ele aparece no case como o método de leitura por trás das regras, e não como marca do portfólio, para separar método autoral de material de candidatura.
