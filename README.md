# lifecycle-lint

![ci](https://github.com/daniloespeleta/lifecycle-lint/actions/workflows/ci.yml/badge.svg)

Jornada de CRM quebrada raramente quebra. Ela roda.

O fluxo dispara, as mensagens saem, o relatório fecha com número verde, e ninguém percebe que dois mil contatos estão presos em três réguas ao mesmo tempo porque cada uma foi publicada por um time diferente. Software tem linter para esse tipo de erro silencioso. CRM não tem.

Isto é um linter para jornadas de lifecycle. Você declara a jornada em YAML, ele aponta o defeito antes que a jornada alcance gente.

```
$ lifecycle-lint audit examples/journeys

winback_inativos · Reengajamento de inativos
   ERRO L001  Jornada ativa sem critério de saída
   ERRO L003 [repete_ate_reagir]  Loop sem limite de iterações
   ERRO L004  Audiência sem lista de supressão
  AVISO L005  Segmento sem decaimento temporal
  AVISO L008  Jornada ativa sem grupo de controle

checkout_abandonado · Recuperação de checkout abandonado
   ERRO L002 [decide_desconto]  Branch sem caminho padrão
   ERRO L012 (com winback_inativos)  Pressão agregada acima do teto por contato
  AVISO L011 (com winback_inativos)  Jornadas ativas concorrendo pela mesma audiência

5 erro(s) · 12 aviso(s) · 0 info
```

O exit code é 1 quando existe erro, então isso roda em CI e barra merge de jornada quebrada.

## O achado que justifica a ferramenta

L011 e L012 não olham uma jornada. Olham o portfólio.

O dano de CRM quase nunca está dentro de um fluxo. Está na soma. Três times publicam três jornadas corretas, todas passariam numa revisão isolada, e o contato recebe onze toques em cinco dias. Ninguém decidiu isso. A soma decidiu. É o único defeito de lifecycle que nenhuma revisão de fluxo único encontra, e é o mais caro: descadastro é a métrica que não volta.

```
   ERRO L012 (com winback_inativos)  Pressão agregada acima do teto por contato
        As jornadas ['checkout_abandonado', 'winback_inativos'] alcançam a mesma
        audiência e somam pressão semanal de 9.5 (teto: 6.0).
        Detalhe: checkout_abandonado (5.5 em 0.2d), winback_inativos (4.0 em 4.0d).
        Ninguém decidiu enviar tudo isso, a soma decidiu.
```

## Instalação

```bash
pip install -e .
lifecycle-lint audit examples/journeys
lifecycle-lint rules
```

Python 3.10+. A única dependência é PyYAML.

## Como uma jornada é declarada

```yaml
id: onboarding_novo_aluno
name: Onboarding novo aluno
status: active

audience:
  segment: matriculados
  filters:
    - field: enrollment_date
      op: within_days
      value: 7
  suppression: [unsubscribed, bounced]
  estimated_size: 42000

entry:
  trigger: event
  event: enrollment.created
  reentry: false

holdout: 0.1
success_metric: ativacao_d14

steps:
  - id: espera_boas_vindas
    type: delay
    hours: 2
  - id: email_boas_vindas
    type: message
    channel: email
    template: welcome_v3

exit:
  - when: event
    event: course.started
  - when: timeout
    after_days: 14
```

Quatro campos fazem o trabalho pesado: `suppression`, `holdout`, `success_metric` e `exit`. São exatamente os quatro que ninguém preenche quando monta o fluxo direto na interface da ferramenta, porque a interface não pergunta.

## As doze regras

| ID | Escopo | O que pega |
|---|---|---|
| L001 | jornada | Jornada ativa sem critério de saída |
| L002 | jornada | Branch sem caminho padrão |
| L003 | jornada | Loop sem limite de iterações |
| L004 | jornada | Audiência sem lista de supressão |
| L005 | jornada | Segmento sem decaimento temporal |
| L006 | jornada | Pressão de mensagem alta dentro da jornada |
| L007 | jornada | Canal intrusivo sem janela de silêncio |
| L008 | jornada | Jornada ativa sem grupo de controle |
| L009 | jornada | Métrica de sucesso ausente ou de vaidade |
| L010 | jornada | Reentrada sem período de carência |
| L011 | portfólio | Jornadas ativas concorrendo pela mesma audiência |
| L012 | portfólio | Pressão agregada acima do teto por contato |

Nenhuma delas é regra de engenharia. Todas são conhecimento de operação de CRM escrito em código, e é essa a tese da ferramenta: o que separa uma régua boa de uma ruim é conhecimento tácito, e conhecimento tácito não escala em revisão manual.

## Duas decisões de projeto que valem a leitura

**A pressão semanal tem piso de sete dias no denominador.** Normalizar pela duração da jornada puniria fluxo curto: três toques em 24 horas não significam vinte e um toques por semana, significam três, porque a jornada acaba. `weekly_pressure = carga × 7 / max(duração_em_dias, 7)`.

**A sobreposição de audiência usa coeficiente de sobreposição, não Jaccard.** Jaccard erra o caso mais comum de CRM, que é uma audiência contida na outra. "Inativos há 60 dias" e "inativos há 60 dias que abandonaram checkout" são a mesma gente, e Jaccard leria 0.5 só porque um dos lados tem um filtro a mais. Dividindo pelo menor conjunto, lê 1.0. Que é a resposta certa.

Os pesos por canal são a terceira decisão, e essa é opinião assumida: e-mail 1.0, push 1.5, SMS e WhatsApp 2.0. WhatsApp custa o dobro de e-mail em atenção. Discorde editando `.lifecycle-lint.yaml`.

## Configuração

Orçamento de atenção é política de CRM, não constante de engenharia. Por isso mora em arquivo versionado, onde a mudança acontece em pull request e não no meio de uma campanha.

```yaml
max_weekly_pressure: 6.0
max_journey_pressure: 4.0
audience_overlap_threshold: 0.6
holdout_required_above: 5000
disabled_rules: []
downgrade_to_warning: [L007]
```

## Sobre o `--explain`

A flag `--explain` pede ao Claude um resumo em prosa dos achados. Ela é opcional por design, e essa é a parte importante.

O diagnóstico inteiro é determinístico. Nenhuma regra chama modelo. Sem `ANTHROPIC_API_KEY` o linter continua correto, só fica menos falante. Colocar um LLM no caminho crítico de uma auditoria troca um resultado reproduzível por um resultado plausível, e resultado plausível não serve para decidir se um fluxo entra no ar.

## Importar do n8n

```python
from lifecycle_lint.adapters import n8n
canonico = n8n.convert("meu_workflow.json")
```

Cobertura parcial, e assumida. O export do n8n descreve execução, não intenção: ele sabe que existe um nó de e-mail, não sabe qual é a métrica de sucesso da jornada. O adaptador marca o que falta como `TODO_DECLARAR` e importa tudo como `draft`, em vez de preencher com padrão silencioso e fazer o linter aprovar uma jornada que ninguém leu.

## Rodando em CI

```yaml
- run: pip install lifecycle-lint
- run: lifecycle-lint audit journeys/ --fail-on error
```

O repositório roda o próprio linter contra `examples/` a cada push: as jornadas com defeito precisam falhar, a corrigida precisa passar. Se um dia inverter, a regra mudou sem ninguém perceber.

## Testes

```bash
pytest -q     # 21 testes
```

Cada regra tem o caso que dispara e o caso limpo que não dispara. Falso positivo em linter de CRM custa caro: o time desliga a ferramenta na segunda semana e nunca mais liga.

## Limitações

Ele lê declaração, não execução. Se a jornada declarada não corresponde ao que está publicado na ferramenta, o linter aprova a declaração e o problema continua em produção. A ponte para isso é o adaptador, e ele hoje cobre n8n parcialmente.

Ele também não sabe se a mensagem é boa. Pressão, saída e medição são estrutura. Conteúdo é outro problema.

## Contexto

Escrito por [Danilo Espeleta](https://espeledata.com), especialista em CRM e lifecycle marketing. As regras vêm de operação real de base com 50 mil leads, não de documentação de ferramenta.

O método de leitura de jornada por trás das regras é o LEEA. O caso completo está em [espeledata.com](https://espeledata.com).

MIT.
