"""Testes por regra.

Cada teste planta um defeito e checa se a regra correspondente o encontra,
e um caso limpo para checar que ela não dispara sozinha. Falso positivo em
linter de CRM custa caro: o time desliga a ferramenta na segunda semana.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from lifecycle_lint import load_journey, load_journeys, run_all
from lifecycle_lint.loader import JourneyParseError
from lifecycle_lint.rules.pressure import weekly_pressure

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

BASE = {
    "id": "teste",
    "name": "Jornada de teste",
    "status": "active",
    "audience": {
        "segment": "base",
        "filters": [{"field": "signup", "op": "within_days", "value": 30}],
        "suppression": ["unsubscribed", "bounced"],
        "estimated_size": 1000,
    },
    "entry": {"trigger": "event", "event": "algo.aconteceu", "reentry": False},
    "success_metric": "ativacao_d14",
    "steps": [
        {"id": "espera", "type": "delay", "days": 3},
        {"id": "email_1", "type": "message", "channel": "email", "template": "t1"},
    ],
    "exit": [{"when": "event", "event": "conversao"}],
}


def build(tmp_path: Path, **overrides) -> Path:
    data = {**BASE, **overrides}
    path = tmp_path / f"{data['id']}.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def ids(findings) -> set[str]:
    return {f.rule_id for f in findings}


def test_baseline_esta_limpo(tmp_path):
    journey = load_journey(build(tmp_path))
    assert run_all([journey]) == []


def test_L001_sem_saida(tmp_path):
    j = load_journey(build(tmp_path, exit=[]))
    assert "L001" in ids(run_all([j]))


def test_L001_ignora_rascunho(tmp_path):
    j = load_journey(build(tmp_path, exit=[], status="draft"))
    assert "L001" not in ids(run_all([j]))


def test_L002_branch_sem_default(tmp_path):
    steps = BASE["steps"] + [
        {"id": "ramifica", "type": "branch", "branches": {"a": [], "b": []}}
    ]
    j = load_journey(build(tmp_path, steps=steps))
    assert "L002" in ids(run_all([j]))

    steps_ok = BASE["steps"] + [
        {"id": "ramifica", "type": "branch", "branches": {"a": [], "default": []}}
    ]
    j_ok = load_journey(build(tmp_path, id="ok", steps=steps_ok))
    assert "L002" not in ids(run_all([j_ok]))


def test_L003_loop_sem_teto(tmp_path):
    steps = BASE["steps"] + [{"id": "repete", "type": "loop"}]
    j = load_journey(build(tmp_path, steps=steps))
    assert "L003" in ids(run_all([j]))


def test_L004_sem_supressao(tmp_path):
    audience = {**BASE["audience"], "suppression": ["unsubscribed"]}
    j = load_journey(build(tmp_path, audience=audience))
    assert "L004" in ids(run_all([j]))


def test_L005_segmento_sem_recencia(tmp_path):
    audience = {
        **BASE["audience"],
        "filters": [{"field": "clicou_alguma_vez", "op": "equals", "value": True}],
    }
    j = load_journey(build(tmp_path, audience=audience))
    assert "L005" in ids(run_all([j]))


def test_L006_pressao_na_jornada(tmp_path):
    steps = [
        {"id": "e1", "type": "message", "channel": "sms", "template": "t"},
        {"id": "e2", "type": "message", "channel": "sms", "template": "t"},
        {"id": "e3", "type": "message", "channel": "whatsapp", "template": "t"},
        {"id": "d", "type": "delay", "days": 1},
    ]
    j = load_journey(build(tmp_path, steps=steps))
    assert "L006" in ids(run_all([j]))


def test_pressao_semanal_nao_pune_jornada_curta(tmp_path):
    """Três toques em 24h são três toques na semana, não vinte e um."""
    steps = [
        {"id": "e1", "type": "message", "channel": "email", "template": "t"},
        {"id": "d1", "type": "delay", "hours": 4},
        {"id": "e2", "type": "message", "channel": "email", "template": "t"},
        {"id": "d2", "type": "delay", "hours": 20},
        {"id": "e3", "type": "message", "channel": "email", "template": "t"},
    ]
    j = load_journey(build(tmp_path, steps=steps))
    assert weekly_pressure(j) == pytest.approx(3.0)


def test_L007_canal_intrusivo_sem_janela(tmp_path):
    steps = BASE["steps"] + [
        {"id": "sms", "type": "message", "channel": "sms", "template": "t"}
    ]
    j = load_journey(build(tmp_path, steps=steps))
    assert "L007" in ids(run_all([j]))

    steps_ok = BASE["steps"] + [
        {
            "id": "sms",
            "type": "message",
            "channel": "sms",
            "template": "t",
            "respects_quiet_hours": True,
        }
    ]
    j_ok = load_journey(build(tmp_path, id="ok", steps=steps_ok))
    assert "L007" not in ids(run_all([j_ok]))


def test_L008_holdout_so_acima_do_limite(tmp_path):
    pequena = {**BASE["audience"], "estimated_size": 900}
    grande = {**BASE["audience"], "estimated_size": 90000}
    assert "L008" not in ids(run_all([load_journey(build(tmp_path, audience=pequena))]))
    assert "L008" in ids(
        run_all([load_journey(build(tmp_path, id="grande", audience=grande))])
    )


def test_L009_metrica_de_vaidade(tmp_path):
    j = load_journey(build(tmp_path, success_metric="open_rate"))
    assert "L009" in ids(run_all([j]))

    sem = load_journey(build(tmp_path, id="sem", success_metric=None))
    findings = [f for f in run_all([sem]) if f.rule_id == "L009"]
    assert findings and findings[0].severity == "error"


def test_L010_reentrada_sem_carencia(tmp_path):
    entry = {**BASE["entry"], "reentry": True}
    j = load_journey(build(tmp_path, entry=entry))
    assert "L010" in ids(run_all([j]))


def test_L011_e_L012_sobreposicao_entre_jornadas(tmp_path):
    a = load_journey(build(tmp_path, id="a"))
    b = load_journey(
        build(
            tmp_path,
            id="b",
            steps=[
                {"id": "m1", "type": "message", "channel": "whatsapp", "template": "t"},
                {"id": "m2", "type": "message", "channel": "sms", "template": "t"},
                {"id": "m3", "type": "message", "channel": "email", "template": "t"},
                {"id": "m4", "type": "message", "channel": "email", "template": "t"},
                {"id": "d", "type": "delay", "days": 2},
            ],
        )
    )
    found = ids(run_all([a, b]))
    assert "L011" in found
    assert "L012" in found


def test_L011_pega_audiencia_que_e_subconjunto_da_outra(tmp_path):
    """O caso que Jaccard erraria: um filtro a mais não é outra audiência."""
    ampla = load_journey(
        build(
            tmp_path,
            id="ampla",
            audience={
                "segment": "inativos",
                "filters": [{"field": "last_login", "op": "more_than_days", "value": 60}],
                "suppression": ["unsubscribed", "bounced"],
                "estimated_size": 1000,
            },
        )
    )
    estreita = load_journey(
        build(
            tmp_path,
            id="estreita",
            audience={
                "segment": "inativos",
                "filters": [
                    {"field": "last_login", "op": "more_than_days", "value": 60},
                    {"field": "checkout_iniciado", "op": "within_days", "value": 3},
                ],
                "suppression": ["unsubscribed", "bounced"],
                "estimated_size": 400,
            },
        )
    )
    assert "L011" in ids(run_all([ampla, estreita]))


def test_L011_nao_dispara_para_audiencias_distintas(tmp_path):
    a = load_journey(build(tmp_path, id="a"))
    b = load_journey(
        build(
            tmp_path,
            id="b",
            audience={
                "segment": "outra_base",
                "filters": [{"field": "compra", "op": "within_days", "value": 10}],
                "suppression": ["unsubscribed", "bounced"],
                "estimated_size": 1000,
            },
        )
    )
    assert "L011" not in ids(run_all([a, b]))


def test_config_desliga_regra(tmp_path):
    j = load_journey(build(tmp_path, exit=[]))
    assert "L001" not in ids(run_all([j], {"disabled_rules": ["L001"]}))


def test_config_rebaixa_severidade(tmp_path):
    j = load_journey(build(tmp_path, exit=[]))
    findings = run_all([j], {"downgrade_to_warning": ["L001"]})
    assert [f.severity for f in findings if f.rule_id == "L001"] == ["warning"]


def test_loader_recusa_status_invalido(tmp_path):
    with pytest.raises(JourneyParseError, match="status"):
        load_journey(build(tmp_path, status="ligada"))


def test_loader_recusa_tipo_de_passo_invalido(tmp_path):
    with pytest.raises(JourneyParseError, match="tipo desconhecido"):
        load_journey(build(tmp_path, steps=[{"id": "x", "type": "telepatia"}]))


def test_exemplos_com_defeito_falham_e_versao_corrigida_passa():
    quebradas = run_all(load_journeys([EXAMPLES / "journeys"]))
    assert any(f.severity == "error" for f in quebradas)

    corrigida = run_all(load_journeys([EXAMPLES / "fixed" / "winback.yaml"]))
    assert [f.rule_id for f in corrigida] == []
