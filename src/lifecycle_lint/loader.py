"""Carrega jornadas do formato canônico YAML para o modelo interno."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .model import Audience, ExitCondition, Filter, Journey, Step


class JourneyParseError(ValueError):
    """O arquivo existe mas não descreve uma jornada válida."""


REQUIRED_TOP_LEVEL = {"id", "name", "status", "audience", "entry", "steps"}
VALID_STATUS = {"active", "draft", "paused", "archived"}
VALID_STEP_TYPES = {"message", "delay", "branch", "loop", "update", "webhook"}


def _parse_filters(raw: list[dict[str, Any]] | None) -> list[Filter]:
    out: list[Filter] = []
    for item in raw or []:
        if "field" not in item or "op" not in item:
            raise JourneyParseError(f"filtro sem 'field' ou 'op': {item!r}")
        out.append(Filter(field=item["field"], op=item["op"], value=item.get("value")))
    return out


def _parse_audience(raw: dict[str, Any]) -> Audience:
    if "segment" not in raw:
        raise JourneyParseError("audience precisa de 'segment'")
    return Audience(
        segment=raw["segment"],
        filters=_parse_filters(raw.get("filters")),
        suppression=list(raw.get("suppression") or []),
        estimated_size=raw.get("estimated_size"),
    )


def _parse_step(raw: dict[str, Any]) -> Step:
    if "id" not in raw or "type" not in raw:
        raise JourneyParseError(f"step sem 'id' ou 'type': {raw!r}")
    if raw["type"] not in VALID_STEP_TYPES:
        raise JourneyParseError(
            f"step '{raw['id']}' tem tipo desconhecido '{raw['type']}'. "
            f"Tipos válidos: {sorted(VALID_STEP_TYPES)}"
        )
    return Step(
        id=raw["id"],
        type=raw["type"],
        channel=raw.get("channel"),
        template=raw.get("template"),
        hours=_as_hours(raw),
        branches=raw.get("branches") or {},
        max_iterations=raw.get("max_iterations"),
        respects_quiet_hours=raw.get("respects_quiet_hours"),
        raw=raw,
    )


def _as_hours(raw: dict[str, Any]) -> float | None:
    if "hours" in raw:
        return float(raw["hours"])
    if "days" in raw:
        return float(raw["days"]) * 24
    if "minutes" in raw:
        return float(raw["minutes"]) / 60
    return None


def _parse_exits(raw: list[dict[str, Any]] | None) -> list[ExitCondition]:
    out: list[ExitCondition] = []
    for item in raw or []:
        out.append(
            ExitCondition(
                when=item.get("when", "event"),
                event=item.get("event"),
                after_days=item.get("after_days"),
                note=item.get("note"),
            )
        )
    return out


def load_journey(path: str | Path) -> Journey:
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise JourneyParseError(f"{path}: YAML inválido. {exc}") from exc

    if not isinstance(raw, dict):
        raise JourneyParseError(f"{path}: esperava um mapa no topo do arquivo")

    missing = REQUIRED_TOP_LEVEL - raw.keys()
    if missing:
        raise JourneyParseError(f"{path}: faltam campos obrigatórios: {sorted(missing)}")

    if raw["status"] not in VALID_STATUS:
        raise JourneyParseError(
            f"{path}: status '{raw['status']}' inválido. Válidos: {sorted(VALID_STATUS)}"
        )

    entry = raw["entry"] or {}
    journey = Journey(
        id=raw["id"],
        name=raw["name"],
        status=raw["status"],
        audience=_parse_audience(raw["audience"]),
        steps=[_parse_step(s) for s in raw["steps"]],
        entry_trigger=entry.get("trigger", "event"),
        entry_event=entry.get("event"),
        reentry=bool(entry.get("reentry", False)),
        reentry_cooldown_days=entry.get("reentry_cooldown_days"),
        exits=_parse_exits(raw.get("exit")),
        holdout=raw.get("holdout"),
        success_metric=raw.get("success_metric"),
        owner=raw.get("owner"),
        source_path=str(path),
    )
    return journey


def load_journeys(paths: list[str | Path]) -> list[Journey]:
    expanded: list[Path] = []
    for p in paths:
        p = Path(p)
        if p.is_dir():
            expanded.extend(sorted(p.rglob("*.yaml")) + sorted(p.rglob("*.yml")))
        else:
            expanded.append(p)
    return [load_journey(p) for p in expanded]
