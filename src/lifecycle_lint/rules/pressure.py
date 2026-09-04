"""Regras de pressão: quanto de atenção o portfólio inteiro cobra de uma pessoa.

O defeito mais caro de CRM raramente está dentro de uma jornada. Está na soma:
três times publicam três fluxos corretos e o contato recebe onze mensagens em
cinco dias. Nenhum linter de fluxo único encontra isso.
"""

from __future__ import annotations

from collections.abc import Iterable
from itertools import combinations

from ..model import CHANNEL_COST, Finding, Journey
from . import journey_rule, portfolio_rule

INTRUSIVE = {"sms", "push", "whatsapp"}


def weekly_pressure(j: Journey) -> float:
    """Carga de atenção que a jornada cobra dentro de uma janela de 7 dias.

    Normalizar por `span` puro puniria jornadas curtas: um fluxo de carrinho
    abandonado com três toques em 24h não significa 21 toques por semana, ele
    acaba. O piso de 7 dias no denominador mede o que a pessoa de fato recebe
    na semana em que a jornada roda.
    """
    span_days = max(j.total_duration_hours / 24, 0.0)
    return j.message_load * 7 / max(span_days, 7.0)


@journey_rule("L006", "Pressão de mensagem alta dentro da jornada")
def journey_pressure(j: Journey, cfg: dict) -> Iterable[Finding]:
    if not j.is_live:
        return
    span_days = j.total_duration_hours / 24
    weekly = weekly_pressure(j)
    if weekly <= cfg["max_journey_pressure"]:
        return
    yield Finding(
        rule_id="L006",
        severity="warning",
        journey_id=j.id,
        title="Pressão de mensagem alta dentro da jornada",
        detail=(
            f"{len(j.messages)} mensagens em {span_days:.1f} dias dão pressão semanal "
            f"de {weekly:.1f} (teto configurado: {cfg['max_journey_pressure']:.1f}). "
            "Peso por canal: e-mail 1.0, push 1.5, SMS e WhatsApp 2.0."
        ),
        fix="Espaçar os delays, cortar a mensagem de menor lift, ou migrar um toque intrusivo para e-mail.",
    )


@journey_rule("L007", "Canal intrusivo sem janela de silêncio")
def intrusive_without_quiet_hours(j: Journey, cfg: dict) -> Iterable[Finding]:
    if not j.is_live:
        return
    for step in j.messages:
        if (step.channel or "").lower() not in INTRUSIVE:
            continue
        if step.respects_quiet_hours:
            continue
        yield Finding(
            rule_id="L007",
            severity="warning",
            journey_id=j.id,
            step_id=step.id,
            title="Canal intrusivo sem janela de silêncio",
            detail=(
                f"O passo '{step.id}' envia por {step.channel} sem declarar "
                "respects_quiet_hours. O gatilho não escolhe a hora: quem dispara o "
                f"evento às 3h da manhã recebe {step.channel} às 3h da manhã."
            ),
            fix=f"Declarar 'respects_quiet_hours: true' em '{step.id}' e fixar a janela no nível da conta.",
        )


def _overlap(a: Journey, b: Journey) -> float:
    """Coeficiente de sobreposição entre duas definições de audiência.

    Jaccard seria a escolha ingênua, e erra o caso mais comum de CRM: uma
    audiência que é subconjunto da outra. 'Inativos há 60 dias' e 'inativos
    há 60 dias que abandonaram checkout' descrevem gente que se encontra,
    e Jaccard leria 0.5 porque um dos lados tem um filtro a mais. O
    coeficiente de sobreposição divide pelo menor dos dois conjuntos e lê 1.0,
    que é a resposta certa: todo mundo do segundo grupo está no primeiro.
    """
    sa, sb = a.audience.signature, b.audience.signature
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / min(len(sa), len(sb))


@portfolio_rule("L011", "Jornadas ativas concorrendo pela mesma audiência")
def overlapping_audiences(journeys: list[Journey], cfg: dict) -> Iterable[Finding]:
    live = [j for j in journeys if j.is_live]
    threshold = cfg["audience_overlap_threshold"]
    for a, b in combinations(live, 2):
        score = _overlap(a, b)
        if score < threshold:
            continue
        yield Finding(
            rule_id="L011",
            severity="warning",
            journey_id=a.id,
            related=[b.id],
            title="Jornadas ativas concorrendo pela mesma audiência",
            detail=(
                f"'{a.name}' e '{b.name}' compartilham {score:.0%} da definição de audiência "
                "e estão ativas ao mesmo tempo. A mesma pessoa está em duas conversas, e o "
                "resultado de cada uma é contaminado pela outra."
            ),
            fix=(
                f"Declarar prioridade entre as duas, ou excluir mutuamente: suprimir de "
                f"'{b.id}' quem está ativo em '{a.id}'."
            ),
        )


@portfolio_rule("L012", "Pressão agregada acima do teto por contato")
def aggregate_pressure(journeys: list[Journey], cfg: dict) -> Iterable[Finding]:
    live = [j for j in journeys if j.is_live]
    threshold = cfg["audience_overlap_threshold"]
    seen: set[frozenset[str]] = set()

    for anchor in live:
        cohort = [j for j in live if _overlap(anchor, j) >= threshold or j is anchor]
        if len(cohort) < 2:
            continue
        key = frozenset(j.id for j in cohort)
        if key in seen:
            continue
        seen.add(key)

        total = sum(weekly_pressure(j) for j in cohort)
        if total <= cfg["max_weekly_pressure"]:
            continue

        breakdown = ", ".join(
            f"{j.id} ({weekly_pressure(j):.1f} em {j.total_duration_hours / 24:.1f}d)"
            for j in cohort
        )
        yield Finding(
            rule_id="L012",
            severity="error",
            journey_id=anchor.id,
            related=sorted(k for k in key if k != anchor.id),
            title="Pressão agregada acima do teto por contato",
            detail=(
                f"As jornadas {sorted(key)} alcançam a mesma audiência e somam pressão "
                f"semanal de {total:.1f} (teto: {cfg['max_weekly_pressure']:.1f}). "
                f"Detalhe: {breakdown}. Ninguém decidiu enviar tudo isso, a soma decidiu."
            ),
            fix=(
                "Instituir um teto de frequência no nível do contato, não no da jornada, "
                "e uma ordem de prioridade que suprime as jornadas de menor valor quando o teto estoura."
            ),
        )


__all__ = ["CHANNEL_COST"]
