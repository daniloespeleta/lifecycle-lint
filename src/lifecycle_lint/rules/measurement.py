"""Regras de medição: a jornada consegue provar que funcionou?

Uma jornada sem holdout e com métrica de vaidade não é uma hipótese testável,
é uma opinião com cronograma.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..model import VANITY_METRICS, Finding, Journey
from . import journey_rule


@journey_rule("L008", "Jornada ativa sem grupo de controle")
def no_holdout(j: Journey, cfg: dict) -> Iterable[Finding]:
    if not j.is_live:
        return
    size = j.audience.estimated_size or 0
    if size < cfg["holdout_required_above"]:
        return
    if j.holdout and j.holdout > 0:
        return
    yield Finding(
        rule_id="L008",
        severity="warning",
        journey_id=j.id,
        title="Jornada ativa sem grupo de controle",
        detail=(
            f"Audiência estimada de {size:,}".replace(",", ".")
            + " contatos e nenhum holdout declarado. "
            "Sem grupo de controle, o resultado da jornada é indistinguível do que "
            "a pessoa faria sozinha, e a jornada leva crédito por conversão que já aconteceria."
        ),
        fix="Declarar 'holdout: 0.1' e comparar a coorte tratada com a retida no mesmo intervalo.",
    )


@journey_rule("L009", "Métrica de sucesso ausente ou de vaidade")
def weak_success_metric(j: Journey, cfg: dict) -> Iterable[Finding]:
    if not j.is_live:
        return
    metric = (j.success_metric or "").strip().lower()
    if not metric:
        yield Finding(
            rule_id="L009",
            severity="error",
            journey_id=j.id,
            title="Jornada ativa sem métrica de sucesso",
            detail=(
                "A jornada não declara o que ela existe para mover. Sem isso, não há "
                "critério para desligá-la, e jornada que não pode ser desligada vira móvel."
            ),
            fix="Declarar 'success_metric' com uma métrica de comportamento, não de entrega.",
        )
        return

    normalized = metric.replace(" ", "_")
    if any(v in normalized for v in VANITY_METRICS):
        yield Finding(
            rule_id="L009",
            severity="warning",
            journey_id=j.id,
            title="Métrica de sucesso é métrica de entrega",
            detail=(
                f"A métrica declarada é '{j.success_metric}'. Isso mede se a mensagem "
                "chegou e foi aberta, não se a pessoa fez o que a jornada queria. "
                "Open rate melhora trocando assunto, e trocar assunto não retém ninguém."
            ),
            fix=(
                "Trocar por uma métrica de comportamento a jusante: ativação em D+14, "
                "segunda compra em 30 dias, retenção da coorte, receita incremental sobre o holdout."
            ),
        )
