# A suíte: três repos, uma tese

## A tese

A tese que une os três projetos é uma só: **jornada de cliente é artefato versionável**. Se ela pode ser declarada, pode ser lida, auditada, testada e revisada em pull request, como código. Hoje ela vive dentro da interface de uma ferramenta de automação, onde ninguém consegue revisar, comparar versões ou explicar por que aquele delay é de 48 horas.

Os três repos são os três momentos desse ciclo.

| Repo | Momento | Certificação que ele exercita |
|---|---|---|
| `lifecycle-lint` | auditar | Claude Code in Action (Anthropic) |
| `segment-brief` | propor | Agents and Workflows (OpenAI Academy) |
| `lentes` | ler | AI Fluency: Framework & Foundations (Anthropic) |

Eles se encaixam num pipeline, e é o encaixe que faz a suíte valer mais que a soma:

```
lentes            →  segment-brief        →  lifecycle-lint
prompts versionados  agente que propõe       linter que audita
e avaliados          jornada em YAML         antes do envio
```

A saída de um é a entrada do outro. O critério de aceite do agente é objetivo: a jornada que ele propõe precisa passar no linter. Isso resolve o problema mais chato de portfólio com IA, que é não ter como provar que o output presta.

## Ordem de construção e por quê

**1. `lifecycle-lint` (pronto).** Primeiro porque é o único que um gestor de CRM entende em cinco segundos e reconhece como dor própria. Também é o que sustenta os outros dois: sem o linter, o agente não tem critério de aceite.

**2. `segment-brief`.** Segundo porque é o que rende mais em entrevista técnica. Toda vaga de CRM sênior em 2026 pergunta sobre IA, e a resposta média é "uso ChatGPT para copy". A resposta com um agente auditável em cima é outra conversa.

**3. `lentes`.** Terceiro porque é o mais fácil de parecer bonito e o mais difícil de provar. Sozinho, seria mais um repositório de prompts, e o mundo não precisa de mais um. Com o harness de avaliação e ligado aos outros dois, vira infraestrutura.

Estimativa honesta: `segment-brief` são cerca de quatro dias de trabalho concentrado, `lentes` são dois. Não sete semanas.

---

# Projeto 2: `segment-brief`

**Uma frase:** agente que lê uma tabela de eventos de produto e devolve o briefing de segmento com a jornada proposta em YAML, já auditada pelo `lifecycle-lint`.

## O problema real

A pergunta "que segmento a gente deveria estar trabalhando" leva uma semana para ser respondida em quase toda operação. Alguém puxa dado, alguém cruza com receita, alguém escreve um documento, alguém discorda. O trabalho não é difícil, é repetitivo, e a parte repetitiva é justamente a que dá para delegar.

## Arquitetura

Roteador determinístico na frente, agente no meio, validador no fim.

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
       · se falhar, devolve os achados ao agente para uma segunda rodada
       · duas rodadas e para: agente que não converge em duas tentativas
         não converge em dez, só gasta token
```

## O que este projeto prova, que os outros não provam

O critério de quando **não** usar agente. O roteador é código. O validador é código. O agente só ocupa o miolo, que é onde a tarefa é aberta o suficiente para justificar. Um agente que também roteia e também valida a si mesmo é um agente que não pode ser auditado.

E prova o loop fechado: a proposta é rejeitada por um programa, não por opinião.

## Escopo e dados

Dataset sintético de edtech, gerado por script versionado: 40 mil usuários, 18 meses de eventos (matrícula, login, aula assistida, pagamento, cancelamento), com sazonalidade e uma coorte de churn plantada para o agente encontrar. Dado sintético é obrigatório aqui, e diz isso em voz alta no README: usar base real de empregador em portfólio público é problema, não é iniciativa.

## Critério de pronto

- Três perguntas de exemplo rodando ponta a ponta, com transcrição do loop salva em `runs/`
- Toda jornada proposta passa no `lifecycle-lint` com `--fail-on error`
- Um eval com dez perguntas e resposta esperada, rodando em CI
- Custo por execução medido e impresso no fim do relatório
- README que explica por que o roteador não é o modelo

---

# Projeto 3: `lentes`

**Uma frase:** biblioteca de lentes de leitura para tarefas de CRM, versionadas, com harness que mede se elas continuam funcionando quando o prompt ou o modelo muda.

## O problema real

Prompt é interface, mas tratado como texto: cola no chat, funciona, salva no Notion, esquece. Seis meses depois o modelo mudou, o prompt degradou, e ninguém percebeu porque não havia com o que comparar.

## O que é uma lente

Uma lente é uma chave de leitura aplicada a um objeto de CRM. Cada uma vira um arquivo com quatro partes, e as quatro correspondem às competências do framework de AI Fluency, que é o ponto de contato com a certificação:

| Parte do arquivo | Competência | O que é na prática |
|---|---|---|
| `task` | Delegation | o que se está delegando ao modelo, e o que fica com o humano |
| `prompt` | Description | a instrução, versionada, com histórico |
| `checks` | Discernment | como se sabe que a saída presta, em asserção verificável |
| `provenance` | Diligence | modelo, data, quem revisou, o que a saída não pode ser usada para decidir |

Lentes iniciais, todas tiradas de trabalho que já é feito à mão toda semana:

1. **Nomear segmento**: recebe a definição técnica do filtro, devolve o nome que o time vai usar na reunião. Nome de segmento é decisão de linguagem, e segmento com nome ruim morre.
2. **Diagnóstico de queda**: recebe série temporal de uma métrica de campanha, devolve as três hipóteses mais prováveis ordenadas por facilidade de testar.
3. **Copy por estágio**: recebe estágio de ciclo de vida e proposta de valor, devolve variações de assunto e primeira linha, com a hipótese que cada variação testa.
4. **Leitura de cancelamento**: recebe respostas abertas de pesquisa de churn, devolve os eixos de motivo com contagem e citação de apoio, sem inventar categoria que não aparece no texto.
5. **Auditoria de tom**: recebe uma régua inteira e aponta onde o registro quebra entre mensagens.

## O harness

O que separa este repo de mais um repositório de prompts:

```bash
lentes eval nomear-segmento          # roda os casos, mostra o placar
lentes eval --all --model sonnet     # troca o modelo, compara com o anterior
lentes diff nomear-segmento v3 v4    # o que mudou entre as versões do prompt
```

Cada lente tem entre cinco e dez casos com asserção verificável. Nem toda asserção precisa de modelo: "não contém travessão", "devolve entre 3 e 5 itens", "não cita nome próprio que não estava na entrada" são checagens de código. As que precisam de julgamento usam um modelo como juiz, e isso fica marcado no relatório, porque juiz-modelo é medida com viés e quem lê o número precisa saber.

## Critério de pronto

- Cinco lentes com dez casos cada
- Placar de regressão rodando em CI, com comparação contra a versão anterior
- Uma lente com histórico de versão real, mostrando o prompt v1 falhando em dois casos e o v3 passando
- README que diz o que a biblioteca não resolve

---

## Sobre nome de suíte

`journey-as-code` como guarda-chuva, se você quiser um. É legível para recrutador técnico e diz a tese sem adjetivo.

Fica de fora dos nomes de repositório o LEEA. Ele aparece no case como o método de leitura por trás das regras, não como marca do portfólio. Método autoral e vitrine de emprego são coisas diferentes, e queimar o primeiro na segunda é troca ruim.
