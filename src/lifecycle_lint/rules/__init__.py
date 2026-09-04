"""Registro de regras.

Uma regra é uma função que recebe jornadas e devolve Findings. Duas famílias:

- `journey_rule`: olha uma jornada isolada. Pega defeito de construção.
- `portfolio_rule`: avalia todas as jornadas ativas em conjunto. Cobre o
  defeito que só existe na interseção entre jornadas, tipicamente produzido
  por times distintos publicando réguas sobre audiências sobrepostas.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from ..model import Finding, Journey

JourneyRuleFn = Callable[[Journey, dict], Iterable[Finding]]
PortfolioRuleFn = Callable[[list[Journey], dict], Iterable[Finding]]


@dataclass
class Rule:
    id: str
    scope: str  # "journey" | "portfolio"
    title: str
    fn: JourneyRuleFn | PortfolioRuleFn


REGISTRY: dict[str, Rule] = {}


def journey_rule(rule_id: str, title: str):
    def deco(fn: JourneyRuleFn) -> JourneyRuleFn:
        REGISTRY[rule_id] = Rule(id=rule_id, scope="journey", title=title, fn=fn)
        return fn

    return deco


def portfolio_rule(rule_id: str, title: str):
    def deco(fn: PortfolioRuleFn) -> PortfolioRuleFn:
        REGISTRY[rule_id] = Rule(id=rule_id, scope="portfolio", title=title, fn=fn)
        return fn

    return deco


DEFAULT_CONFIG: dict = {
    # Pressão máxima de atenção por contato, por janela de 7 dias, somando
    # todas as jornadas ativas que o alcançam. Unidade: peso de canal.
    "max_weekly_pressure": 6.0,
    # Pressão máxima dentro de uma única jornada.
    "max_journey_pressure": 4.0,
    # Sobreposição de assinatura de audiência a partir da qual duas jornadas
    # são consideradas concorrentes.
    "audience_overlap_threshold": 0.6,
    # Jornadas ativas acima deste alcance estimado exigem holdout.
    "holdout_required_above": 5000,
    # Regras a ignorar, por id.
    "disabled_rules": [],
    # Regras a rebaixar para warning.
    "downgrade_to_warning": [],
}


def run_all(journeys: list[Journey], config: dict | None = None) -> list[Finding]:
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    disabled = set(cfg.get("disabled_rules") or [])
    downgrade = set(cfg.get("downgrade_to_warning") or [])

    findings: list[Finding] = []
    for rule in REGISTRY.values():
        if rule.id in disabled:
            continue
        if rule.scope == "journey":
            for journey in journeys:
                findings.extend(rule.fn(journey, cfg))
        else:
            findings.extend(rule.fn(journeys, cfg))

    for f in findings:
        if f.rule_id in downgrade and f.severity == "error":
            f.severity = "warning"

    order = {"error": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda f: (order[f.severity], f.rule_id, f.journey_id))
    return findings


# Import dos módulos de regra para popular o REGISTRY.
from . import measurement, pressure, structure  # noqa: E402,F401
