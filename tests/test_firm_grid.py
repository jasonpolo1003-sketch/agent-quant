"""scripts/firm_grid.py on synthetic tables only (never the real workbench data)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from test_prop_firms import _draft
from test_prop_play import rec_table

from quant_brain.workbench import engine

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "firm_grid.py"
FP = "f00dfeed" + "0" * 56


def _script():
    spec = importlib.util.spec_from_file_location("firm_grid", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MENU = {
    "id": "TEST",
    "policies": {
        "P1_steady": {
            "combine_size": 2,
            "funded_size": 2,
            "combine_profit_stop": "consistency_safe",
            "funded_profit_stop": None,
        },
        "P2_fast": {
            "combine_size": 6,
            "funded_size": 2,
            "combine_profit_stop": "consistency_safe",
            "funded_profit_stop": "funded_consistency_safe",
        },
    },
    "grid": {"horizon_days": 42, "cost_level": "L3"},
}


def _root(tmp_path: Path, edge=6_000) -> Path:
    (tmp_path / engine.LEDGER).parent.mkdir(parents=True)
    trial = {"fingerprint": FP, "family": "noise_area", "market": "MNQ", "roll": "volume"}
    (tmp_path / engine.LEDGER).write_text(json.dumps(trial) + "\n", encoding="utf-8")
    rec_table(n=250, edge=edge).save(tmp_path / engine.CACHE / f"{FP}.npz")
    menu = tmp_path / "menu.v1.json"
    menu.write_text(json.dumps(MENU), encoding="utf-8")
    sha = hashlib.sha256(menu.read_bytes()).hexdigest()
    (tmp_path / "menu.v1.sha256").write_text(f"{sha}  menu.v1.json\n", encoding="utf-8")
    firms_dir = tmp_path / "firms"
    firms_dir.mkdir()
    (firms_dir / "alpha.json").write_text(json.dumps(_draft()), encoding="utf-8")
    off = _draft(automation_allowed_funded=False)
    (firms_dir / "beta.json").write_text(json.dumps(off), encoding="utf-8")
    return tmp_path


ARGS = ["--menu", "menu.v1.json", "--run", "f00d", "--firms", "firms/*.json"]
SMALL = ["--paths", "40", "--outer", "4", "--inner", "20"]


def test_runner_writes_one_ledger_line_per_cell_and_a_results_file(tmp_path, capsys):
    root = _root(tmp_path)
    assert _script().main([*ARGS, "--topstep", *SMALL], root=root) == 0
    lines = (root / engine.WORKBENCH / "prop_trials.jsonl").read_text(encoding="utf-8").splitlines()
    rows = [json.loads(x) for x in lines]
    # alpha (1 variant) + Topstep adapter (4 variants), x 2 plays; beta is skipped
    assert len(rows) == (1 + 4) * 2
    assert {r["firm_file"] for r in rows} == {"firms/alpha.json", "topstep_50k (adapter)"}
    assert all(r["workbench_fingerprint"] == FP and r["gate"] in ("pass", "fail") for r in rows)
    assert all(
        len(r["net_cash_90ci"]) == 2 and len(r["net_cash_minus_luck_90ci"]) == 2 for r in rows
    )
    (out,) = (root / engine.WORKBENCH / "prop" / "firm_grid").glob("*.json")
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["skipped"] == [
        {"firm_file": "firms/beta.json", "variant": "default", "reason": "automation not allowed"}
    ]
    assert len(res["cells"]) == 10
    alpha = next(
        c for c in res["cells"] if c["firm_file"] == "firms/alpha.json" and c["policy"] == "P2_fast"
    )
    assert (
        alpha["resolved"]["eval"]["size"] == 6 and alpha["resolved"]["funded"]["stop"] is not None
    )
    assert "selected:" in capsys.readouterr().out


def test_runner_refuses_a_changed_menu_a_bad_firm_and_a_table_without_records(tmp_path):
    root = _root(tmp_path)
    mod = _script()
    (root / "menu.v1.json").write_text(json.dumps({**MENU, "id": "edited"}), encoding="utf-8")
    with pytest.raises(SystemExit, match="pinned hash"):
        mod.main([*ARGS, *SMALL], root=root)
    root = _root(tmp_path / "b")
    bad = _draft()
    del bad["funded"]["max_loss_usd"]
    (root / "firms" / "gamma.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(SystemExit, match=r"gamma\.json"):
        mod.main([*ARGS, *SMALL], root=root)
    assert not (root / engine.WORKBENCH / "prop_trials.jsonl").exists()  # nothing half-run
    assert mod.main([*ARGS, *SMALL, "--skip-invalid"], root=root) == 0  # listed, not run
    (out,) = (root / engine.WORKBENCH / "prop" / "firm_grid").glob("*.json")
    res = json.loads(out.read_text(encoding="utf-8"))
    assert [x["firm_file"] for x in res["invalid"]] == ["firms/gamma.json"]
    assert {c["firm_file"] for c in res["cells"]} == {"firms/alpha.json"}
    root = _root(tmp_path / "c")
    from test_prop_simulator import _table

    _table(n=50).save(root / engine.CACHE / f"{FP}.npz")
    with pytest.raises(SystemExit, match="minute records"):
        mod.main([*ARGS, *SMALL], root=root)
