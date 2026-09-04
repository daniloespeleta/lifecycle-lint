# lifecycle-lint

![ci](https://github.com/daniloespeleta/lifecycle-lint/actions/workflows/ci.yml/badge.svg)

Uma jornada de CRM com defeito de construção continua executando. O fluxo dispara, as mensagens saem, o relatório fecha com número positivo, e o contato que já converteu segue recebendo a sequência de quem não converteu. O efeito aparece semanas depois, na taxa de descadastro e na entregabilidade do domínio.

Ferramentas de automação executam o que foi montado na interface. Elas não verificam se a régua tem critério de saída, se o segmento decai no tempo ou se outra régua ativa já está falando com a mesma pessoa. `lifecycle-lint` faz essa verificação a partir da jornada declarada em YAML, antes da publicação.

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

O exit code é 1 quando há erro, o que permite rodar em CI e barrar merge.

## Regras de portfólio

L011 e L012 avaliam o conjunto de jornadas ativas em vez de cada jornada isolada.

O caso que elas cobrem: três times publicam três réguas sobre audiências que se sobrepõem, cada uma correta dentro do próprio escopo, e o contato recebe onze toques em cinco dias. A carga somada não consta de nenhum dos três arquivos, então revisão individual não detecta. L011 mede a sobreposição entre as definições de audiência das jornadas ativas. L012 soma a pressão semanal ponderada que essas jornadas cobram do mesmo contato e compara com o teto configurado.

```
   ERRO L012 (com winback_inativos)  Pressão agregada acima do teto por contato
        As jornadas ['checkout_abandonado', 'winback_inativos'] alcançam a mesma
        audiência e somam pressão semanal de 9.5 (teto: 6.0).
        Detalhe: checkout_abandonado (5.5 em 0.2d), winback_inativos (4.0 em 4.0d).
```

## Instalação

```bash
pip install -e .
lifecycle-lint audit examples/journeys
lifecycle-lint rules
```

Python 3.10 ou maior. A única dependência é PyYAML.

## Formato da jornada

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

Quatro campos concentram a maior parte dos achados: `suppression`, `holdout`, `success_metric` e `exit`. Nenhum deles tem campo equivalente na interface das ferramentas de automação mais usadas, o que explica por que costumam estar ausentes.

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

As doze codificam prática de operação de CRM, não convenção de engenharia de software. `lifecycle-lint rules` lista todas com escopo e título.

## Duas decisões de cálculo

**Pressão semanal com piso de sete dias no denominador.** Normalizar pela duração da jornada superestimaria fluxos curtos: três toques em 24 horas seriam lidos como 21 toques por semana, o que não ocorre, já que a jornada termina. A fórmula é `weekly_pressure = carga × 7 / max(duração_em_dias, 7)`.

**Sobreposição de audiência por coeficiente de sobreposição, não índice de Jaccard.** Quando uma audiência está contida na outra, Jaccard subestima. "Inativos há 60 dias" e "inativos há 60 dias que abandonaram checkout" alcançam o mesmo grupo, e Jaccard retorna 0.5 porque o segundo conjunto tem um filtro a mais. Dividindo pela cardinalidade do menor conjunto, o resultado é 1.0.

Os pesos por canal são parâmetro assumido: e-mail 1.0, push 1.5, SMS e WhatsApp 2.0. A escala reflete intrusividade percebida, e pode ser ajustada em `.lifecycle-lint.yaml`.

## Configuração

Os limites de pressão variam por vertical, tamanho de base e tolerância da audiência. São decisão de operação, então ficam em `.lifecycle-lint.yaml`, versionado no repositório, e qualquer alteração passa por pull request.

```yaml
max_weekly_pressure: 6.0
max_journey_pressure: 4.0
audience_overlap_threshold: 0.6
holdout_required_above: 5000
disabled_rules: []
downgrade_to_warning: [L007]
```

## A flag `--explain`

`--explain` envia os achados ao Claude e imprime um resumo em prosa no stderr, para uso em reunião de revisão. Requer `ANTHROPIC_API_KEY` e o extra `pip install 'lifecycle-lint[explain]'`.

Nenhuma regra chama modelo. O diagnóstico é determinístico e reproduzível, e a camada de explicação opera sobre o resultado já fechado. Sem chave de API, o linter roda normalmente e a flag imprime um aviso.

## Importar do n8n

```python
from lifecycle_lint.adapters import n8n
canonico = n8n.convert("meu_workflow.json")
```

O export do n8n contém os nós do workflow e as conexões entre eles. Não contém métrica de sucesso, holdout, lista de supressão nem critério de saída, porque esses campos são declarados pelo operador e não têm representação no fluxo executável. O adaptador converte os nós que reconhece, marca os campos ausentes como `TODO_DECLARAR` e importa a jornada com status `draft`. Preencher esses campos com valor padrão faria o linter aprovar uma régua que ninguém revisou.

## Rodando em CI

```yaml
- run: pip install lifecycle-lint
- run: lifecycle-lint audit journeys/ --fail-on error
```

O repositório roda o próprio linter contra `examples/` a cada push. As jornadas de exemplo com defeito precisam falhar e a versão corrigida precisa passar, o que detecta mudança acidental de comportamento nas regras.

## Testes

```bash
pytest -q     # 21 testes
```

Cada regra tem um caso que dispara e um caso limpo que não dispara. A cobertura do caso negativo existe para conter falso positivo, que é o motivo mais comum de abandono de linter.

## Limitações

O linter valida o arquivo YAML, e o arquivo pode divergir do fluxo que está publicado na ferramenta de automação. Nesse caso a auditoria passa e o defeito permanece em produção. O adaptador de n8n reduz parte dessa distância, com cobertura hoje limitada aos nós de mensagem, espera, condição e loop.

O linter também não avalia conteúdo de mensagem. As doze regras cobrem estrutura de fluxo, definição de audiência e instrumentação de medida.

## Contexto

Escrito por [Danilo Espeleta](https://espeledata.com), especialista em CRM e lifecycle marketing. As regras derivam de operação de base com 50 mil leads. O método de leitura de jornada por trás delas é o LEEA, e o caso técnico completo está em [espeledata.com](https://espeledata.com).

Licença MIT.
