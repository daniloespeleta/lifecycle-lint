"""Modelo canônico de uma jornada de lifecycle.

A ideia central: uma jornada de CRM é uma máquina de estados sobre pessoas.
Se ela pode ser descrita, ela pode ser auditada antes de entrar no ar.
Este módulo define a descrição. As regras em `rules/` fazem a auditoria.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["error", "warning", "info"]

CHANNEL_COST = {
    # Peso de intrusividade por canal. Usado para calcular pressão de mensagem.
    # Push e SMS custam mais atenção por unidade do que e-mail.
    "email": 1.0,
    "push": 1.5,
    "sms": 2.0,
    "whatsapp": 2.0,
    "in_app": 0.5,
}

VANITY_METRICS = {
    "open_rate",
    "taxa_de_abertura",
    "impressions",
    "impressoes",
    "sends",
    "envios",
    "deliverability",
    "clicks",
    "cliques",
}


@dataclass
class Filter:
    field: str
    op: str
    value: Any = None

    @property
    def is_recency_bound(self) -> bool:
        """O filtro tem decaimento temporal?

        Operadores com janela (`within_days`, `last_n_days`) descrevem um
        conjunto que se renova. Operadores sem janela (`equals`, `exists`)
        descrevem um conjunto que só cresce ao longo do tempo.
        """
        return self.op in {"within_days", "within_hours", "since", "between_dates", "last_n_days"}


@dataclass
class Audience:
    segment: str
    filters: list[Filter] = field(default_factory=list)
    suppression: list[str] = field(default_factory=list)
    estimated_size: int | None = None

    @property
    def signature(self) -> frozenset[str]:
        """Assinatura comparável entre jornadas, para detectar sobreposição."""
        parts = {f"{f.field}:{f.op}:{f.value}" for f in self.filters}
        parts.add(f"segment:{self.segment}")
        return frozenset(parts)


@dataclass
class Step:
    id: str
    type: Literal["message", "delay", "branch", "loop", "update", "webhook"]
    channel: str | None = None
    template: str | None = None
    hours: float | None = None
    branches: dict[str, list[str]] = field(default_factory=dict)
    max_iterations: int | None = None
    respects_quiet_hours: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_message(self) -> bool:
        return self.type == "message"


@dataclass
class ExitCondition:
    when: str
    event: str | None = None
    after_days: int | None = None
    note: str | None = None


@dataclass
class Journey:
    id: str
    name: str
    status: Literal["active", "draft", "paused", "archived"]
    audience: Audience
    steps: list[Step]
    entry_trigger: str
    entry_event: str | None = None
    reentry: bool = False
    reentry_cooldown_days: int | None = None
    exits: list[ExitCondition] = field(default_factory=list)
    holdout: float | None = None
    success_metric: str | None = None
    owner: str | None = None
    source_path: str | None = None

    @property
    def is_live(self) -> bool:
        return self.status == "active"

    @property
    def messages(self) -> list[Step]:
        return [s for s in self.steps if s.is_message]

    @property
    def total_duration_hours(self) -> float:
        return sum(s.hours or 0.0 for s in self.steps if s.type == "delay")

    @property
    def message_load(self) -> float:
        """Custo de atenção total da jornada, ponderado por canal."""
        return sum(CHANNEL_COST.get(s.channel or "email", 1.0) for s in self.messages)


@dataclass
class Finding:
    rule_id: str
    severity: Severity
    journey_id: str
    title: str
    detail: str
    fix: str
    step_id: str | None = None
    related: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "journey_id": self.journey_id,
            "step_id": self.step_id,
            "title": self.title,
            "detail": self.detail,
            "fix": self.fix,
            "related": self.related,
        }
