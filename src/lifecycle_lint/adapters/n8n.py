"""Adaptador n8n → formato canônico.

Cobertura parcial e declarada. O export do n8n contém os nós do workflow e as
conexões entre eles. Métrica de sucesso, holdout, lista de supressão e critério
de saída são campos declarados pelo operador e não têm representação no fluxo
executável, então o adaptador os marca como TODO_DECLARAR e importa a jornada
como draft. Preencher com valor padrão faria o linter aprovar uma régua que
ninguém revisou.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

NODE_MAP = {
    "n8n-nodes-base.emailSend": ("message", "email"),
    "n8n-nodes-base.gmail": ("message", "email"),
    "n8n-nodes-base.twilio": ("message", "sms"),
    "n8n-nodes-base.pushover": ("message", "push"),
    "n8n-nodes-base.wait": ("delay", None),
    "n8n-nodes-base.if": ("branch", None),
    "n8n-nodes-base.switch": ("branch", None),
    "n8n-nodes-base.splitInBatches": ("loop", None),
    "n8n-nodes-base.httpRequest": ("webhook", None),
}

UNDECLARED = "TODO_DECLARAR"


def _wait_to_hours(params: dict[str, Any]) -> float | None:
    amount = params.get("amount")
    if amount is None:
        return None
    unit = params.get("unit", "hours")
    factor = {"seconds": 1 / 3600, "minutes": 1 / 60, "hours": 1.0, "days": 24.0}
    return float(amount) * factor.get(unit, 1.0)


def convert(export_path: str | Path) -> dict[str, Any]:
    raw = json.loads(Path(export_path).read_text(encoding="utf-8"))
    nodes = raw.get("nodes", [])

    steps: list[dict[str, Any]] = []
    for node in nodes:
        mapped = NODE_MAP.get(node.get("type", ""))
        if not mapped:
            continue
        step_type, channel = mapped
        step: dict[str, Any] = {
            "id": node.get("name", node.get("id", "sem_nome")).lower().replace(" ", "_"),
            "type": step_type,
        }
        params = node.get("parameters", {}) or {}
        if channel:
            step["channel"] = channel
            step["template"] = params.get("subject") or params.get("message") or UNDECLARED
        if step_type == "delay":
            step["hours"] = _wait_to_hours(params)
        if step_type == "branch":
            step["branches"] = {"true": [], "false": []}
        steps.append(step)

    return {
        "id": raw.get("name", "importado_n8n").lower().replace(" ", "_"),
        "name": raw.get("name", "Importado do n8n"),
        # Deliberadamente 'draft': um fluxo importado ainda não foi lido por ninguém.
        "status": "draft",
        "_undeclared": [
            "audience.suppression",
            "holdout",
            "success_metric",
            "exit",
        ],
        "audience": {"segment": UNDECLARED, "filters": [], "suppression": []},
        "entry": {"trigger": "event", "event": UNDECLARED},
        "steps": steps,
        "exit": [],
    }
