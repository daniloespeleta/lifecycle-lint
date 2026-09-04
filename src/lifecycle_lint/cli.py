"""Interface de linha de comando."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from .loader import JourneyParseError, load_journeys
from .report import render_json, render_markdown, render_text, summarize
from .rules import DEFAULT_CONFIG, REGISTRY, run_all

CONFIG_NAME = ".lifecycle-lint.yaml"


def load_config(explicit: str | None) -> dict:
    path = Path(explicit) if explicit else Path.cwd() / CONFIG_NAME
    if not path.exists():
        return dict(DEFAULT_CONFIG)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {**DEFAULT_CONFIG, **data}


def cmd_audit(args: argparse.Namespace) -> int:
    try:
        journeys = load_journeys(args.paths)
    except JourneyParseError as exc:
        print(f"erro de leitura: {exc}", file=sys.stderr)
        return 2

    if not journeys:
        print("nenhuma jornada encontrada nos caminhos informados", file=sys.stderr)
        return 2

    config = load_config(args.config)
    findings = run_all(journeys, config)

    if args.format == "json":
        print(render_json(findings, journeys))
    elif args.format == "md":
        print(render_markdown(findings, journeys))
    else:
        color = sys.stdout.isatty() and not args.no_color
        print(render_text(findings, journeys, color=color))

    if args.explain and findings:
        from .explain import explain_findings

        print(explain_findings(findings, journeys), file=sys.stderr)

    counts = summarize(findings)
    if args.fail_on == "none":
        return 0
    if args.fail_on == "warning":
        return 1 if (counts.get("error") or counts.get("warning")) else 0
    return 1 if counts.get("error") else 0


def cmd_rules(args: argparse.Namespace) -> int:
    for rule in sorted(REGISTRY.values(), key=lambda r: r.id):
        scope = "portfólio" if rule.scope == "portfolio" else "jornada"
        print(f"{rule.id}  [{scope:>9}]  {rule.title}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lifecycle-lint",
        description="Audita jornadas de lifecycle antes de elas alcançarem gente.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    audit = sub.add_parser("audit", help="audita arquivos ou diretórios de jornadas")
    audit.add_argument("paths", nargs="+", help="arquivos .yaml ou diretórios")
    audit.add_argument("--format", choices=["text", "json", "md"], default="text")
    audit.add_argument("--config", help=f"caminho do {CONFIG_NAME}")
    audit.add_argument(
        "--fail-on",
        choices=["error", "warning", "none"],
        default="error",
        help="qual severidade derruba o exit code (padrão: error)",
    )
    audit.add_argument("--no-color", action="store_true")
    audit.add_argument(
        "--explain",
        action="store_true",
        help="pede ao Claude uma leitura em prosa dos achados (requer ANTHROPIC_API_KEY)",
    )
    audit.set_defaults(func=cmd_audit)

    rules = sub.add_parser("rules", help="lista as regras disponíveis")
    rules.set_defaults(func=cmd_rules)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
