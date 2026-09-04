"""Camada opcional de explicação em linguagem natural.

Critério de projeto, e é ele que importa mais que o código deste arquivo:
o diagnóstico é determinístico, a explicação é generativa. Nenhuma regra
depende do modelo. Se a chave de API não existir, o linter continua correto,
só fica menos falante. Um LLM no caminho crítico de uma auditoria transforma
um resultado reproduzível em um resultado plausível, e auditoria plausível
não serve para decidir se um fluxo entra no ar.
"""

from __future__ import annotations

import os
import textwrap

from .model import Finding, Journey

SYSTEM = textwrap.dedent(
    """
    Você lê relatórios de auditoria de jornadas de CRM e escreve o resumo que
    o gestor de lifecycle leria antes da reunião de revisão.

    Regras: não invente achados além dos fornecidos. Ordene por dano provável
    ao contato, não por severidade formal. Diga qual achado consertar primeiro
    e por quê. Máximo seis frases. Sem travessão, sem bullet decorativo.
    """
).strip()


def build_prompt(findings: list[Finding], journeys: list[Journey]) -> str:
    lines = [f"Jornadas auditadas: {', '.join(j.id for j in journeys)}", "", "Achados:"]
    for f in findings:
        lines.append(
            f"- [{f.severity}] {f.rule_id} em {f.journey_id}"
            + (f"/{f.step_id}" if f.step_id else "")
            + f": {f.title}. {f.detail}"
        )
    return "\n".join(lines)


def explain_findings(findings: list[Finding], journeys: list[Journey]) -> str:
    prompt = build_prompt(findings, journeys)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        return (
            "\n[--explain] ANTHROPIC_API_KEY não definida. O diagnóstico acima está "
            "completo e é determinístico; a explicação em prosa é opcional por design."
        )

    try:
        import anthropic
    except ImportError:
        return "\n[--explain] instale o extra: pip install 'lifecycle-lint[explain]'"

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=os.environ.get("LIFECYCLE_LINT_MODEL", "claude-sonnet-4-5"),
        max_tokens=600,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    body = "".join(block.text for block in message.content if block.type == "text")
    return "\n[--explain]\n" + body
