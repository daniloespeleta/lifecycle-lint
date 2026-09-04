"""Regras de construção da jornada: por onde a pessoa entra, e por onde sai."""

from __future__ import annotations

from collections.abc import Iterable

from ..model import Finding, Journey
from . import journey_rule


@journey_rule("L001", "Jornada ativa sem critério de saída")
def no_exit_criteria(j: Journey, cfg: dict) -> Iterable[Finding]:
    if not j.is_live:
        return
    if j.exits:
        return
    yield Finding(
        rule_id="L001",
        severity="error",
        journey_id=j.id,
        title="Jornada ativa sem critério de saída",
        detail=(
            "A jornada não declara nenhuma condição de saída. Quem entra só sai "
            "quando os passos acabam, mesmo que já tenha feito a conversão que a "
            "jornada existe para provocar. É assim que um aluno matriculado continua "
            "recebendo o fluxo de quem não matriculou."
        ),
        fix=(
            "Declarar em 'exit' o evento que torna a jornada desnecessária "
            "(a própria conversão) e um teto de tempo. Exemplo:\n"
            "exit:\n  - when: event\n    event: course.started\n"
            "  - when: timeout\n    after_days: 30"
        ),
    )


@journey_rule("L002", "Branch sem caminho padrão")
def branch_without_default(j: Journey, cfg: dict) -> Iterable[Finding]:
    for step in j.steps:
        if step.type != "branch":
            continue
        keys = {k.lower() for k in step.branches}
        if keys & {"default", "else", "otherwise", "padrao", "padrão"}:
            continue
        yield Finding(
            rule_id="L002",
            severity="error",
            journey_id=j.id,
            step_id=step.id,
            title="Branch sem caminho padrão",
            detail=(
                f"O passo '{step.id}' ramifica em {sorted(step.branches)} e não tem "
                "caminho padrão. Quem não cair em nenhuma condição para na bifurcação "
                "e some do relatório: não converteu, não saiu, não aparece em lugar nenhum."
            ),
            fix=f"Adicionar uma chave 'default' em branches de '{step.id}', nem que seja para sair da jornada.",
        )


@journey_rule("L003", "Loop sem limite de iterações")
def loop_without_limit(j: Journey, cfg: dict) -> Iterable[Finding]:
    for step in j.steps:
        if step.type == "loop" and not step.max_iterations:
            yield Finding(
                rule_id="L003",
                severity="error",
                journey_id=j.id,
                step_id=step.id,
                title="Loop sem limite de iterações",
                detail=(
                    f"O passo '{step.id}' repete sem teto declarado. Um loop de "
                    "reengajamento sem limite não reengaja, persegue."
                ),
                fix=f"Definir 'max_iterations' em '{step.id}' e uma saída para quem estourar o limite.",
            )


@journey_rule("L004", "Audiência sem lista de supressão")
def no_suppression(j: Journey, cfg: dict) -> Iterable[Finding]:
    if not j.is_live or not j.messages:
        return
    required = {"unsubscribed", "bounced"}
    present = {s.lower() for s in j.audience.suppression}
    missing = required - present
    if not missing:
        return
    yield Finding(
        rule_id="L004",
        severity="error",
        journey_id=j.id,
        title="Audiência sem lista de supressão",
        detail=(
            f"A audiência não suprime {sorted(missing)}. Enviar para quem pediu para sair "
            "é problema de compliance antes de ser problema de entregabilidade, e queima "
            "reputação de domínio que leva meses para recuperar."
        ),
        fix="Adicionar em audience.suppression: [unsubscribed, bounced, complained].",
    )


@journey_rule("L005", "Segmento sem decaimento temporal")
def segment_without_recency(j: Journey, cfg: dict) -> Iterable[Finding]:
    if not j.audience.filters:
        yield Finding(
            rule_id="L005",
            severity="warning",
            journey_id=j.id,
            title="Segmento sem nenhum filtro",
            detail=(
                f"A audiência é o segmento '{j.audience.segment}' inteiro, sem recorte. "
                "Segmento sem recorte é lista, e lista não é segmento."
            ),
            fix="Adicionar ao menos um filtro com janela temporal em audience.filters.",
        )
        return
    if any(f.is_recency_bound for f in j.audience.filters):
        return
    fields = [f.field for f in j.audience.filters]
    yield Finding(
        rule_id="L005",
        severity="warning",
        journey_id=j.id,
        title="Segmento sem decaimento temporal",
        detail=(
            f"Os filtros {fields} não têm janela de tempo. Um segmento definido por "
            "'já fez alguma vez' só cresce e nunca esquece: em seis meses ele contém "
            "gente que não interage há um ano, e a métrica da jornada passa a medir "
            "o tamanho do histórico, não o comportamento atual."
        ),
        fix="Trocar ao menos um filtro por um operador com janela: within_days, last_n_days, since.",
    )


@journey_rule("L010", "Reentrada sem período de carência")
def reentry_without_cooldown(j: Journey, cfg: dict) -> Iterable[Finding]:
    if j.reentry and not j.reentry_cooldown_days:
        yield Finding(
            rule_id="L010",
            severity="warning",
            journey_id=j.id,
            title="Reentrada sem período de carência",
            detail=(
                "A jornada permite reentrada sem carência. Quem dispara o gatilho três "
                "vezes na mesma semana recebe a sequência inteira três vezes."
            ),
            fix="Definir entry.reentry_cooldown_days com a duração da própria jornada, no mínimo.",
        )
