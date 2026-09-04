"""Formatação do relatório: terminal, JSON e Markdown."""

from __future__ import annotations

import json
from collections import Counter

from .model import Finding, Journey

SEV_LABEL = {"error": "ERRO", "warning": "AVISO", "info": "INFO"}
SEV_COLOR = {"error": "\033[31m", "warning": "\033[33m", "info": "\033[36m"}
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _c(text: str, code: str, color: bool) -> str:
    return f"{code}{text}{RESET}" if color else text


def summarize(findings: list[Finding]) -> Counter:
    return Counter(f.severity for f in findings)


def render_text(findings: list[Finding], journeys: list[Journey], color: bool = True) -> str:
    lines: list[str] = []
    counts = summarize(findings)

    lines.append(
        _c(f"lifecycle-lint · {len(journeys)} jornada(s) auditada(s)", BOLD, color)
    )
    lines.append("")

    if not findings:
        lines.append("Nenhum achado. As jornadas declaram saída, supressão, teto e métrica.")
        return "\n".join(lines)

    by_journey: dict[str, list[Finding]] = {}
    for f in findings:
        by_journey.setdefault(f.journey_id, []).append(f)

    for journey_id, items in by_journey.items():
        journey = next((j for j in journeys if j.id == journey_id), None)
        title = f"{journey_id}" + (f" · {journey.name}" if journey else "")
        lines.append(_c(title, BOLD, color))
        for f in items:
            tag = _c(f"{SEV_LABEL[f.severity]:>5}", SEV_COLOR[f.severity], color)
            loc = f" [{f.step_id}]" if f.step_id else ""
            rel = f" (com {', '.join(f.related)})" if f.related else ""
            lines.append(f"  {tag} {f.rule_id}{loc}{rel}  {f.title}")
            for para in f.detail.split("\n"):
                lines.append(f"        {para}")
            fix_head, *fix_rest = f.fix.split("\n")
            lines.append(f"        {_c('correção:', DIM, color)} {fix_head}")
            for extra in fix_rest:
                lines.append(f"          {extra}")
            lines.append("")
        lines.append("")

    parts = [
        f"{counts.get('error', 0)} erro(s)",
        f"{counts.get('warning', 0)} aviso(s)",
        f"{counts.get('info', 0)} info",
    ]
    lines.append(_c(" · ".join(parts), BOLD, color))
    return "\n".join(lines)


def render_json(findings: list[Finding], journeys: list[Journey]) -> str:
    counts = summarize(findings)
    payload = {
        "journeys_audited": [j.id for j in journeys],
        "summary": {
            "error": counts.get("error", 0),
            "warning": counts.get("warning", 0),
            "info": counts.get("info", 0),
        },
        "findings": [f.as_dict() for f in findings],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_markdown(findings: list[Finding], journeys: list[Journey]) -> str:
    counts = summarize(findings)
    out = [
        "# Auditoria de jornadas",
        "",
        f"{len(journeys)} jornada(s) auditada(s) · "
        f"**{counts.get('error', 0)} erros** · {counts.get('warning', 0)} avisos",
        "",
    ]
    if not findings:
        out.append("Nenhum achado.")
        return "\n".join(out)

    out += ["| Severidade | Regra | Jornada | Achado |", "|---|---|---|---|"]
    for f in findings:
        where = f.journey_id + (f" / {f.step_id}" if f.step_id else "")
        out.append(f"| {SEV_LABEL[f.severity]} | {f.rule_id} | {where} | {f.title} |")
    out.append("")

    for f in findings:
        out += [
            f"### {f.rule_id} · {f.title}",
            "",
            f"**Onde:** `{f.journey_id}`" + (f" / `{f.step_id}`" if f.step_id else ""),
            "",
            f.detail,
            "",
            "**Correção**",
            "",
            "```",
            f.fix,
            "```",
            "",
        ]
    return "\n".join(out)
