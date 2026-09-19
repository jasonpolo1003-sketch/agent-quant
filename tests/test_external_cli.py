import json

from test_external_intake import native_pdf

from quant_brain.config import PROJECT_ROOT
from quant_brain.research import external_cli


def test_cli_import_reimport_list_and_dry_handoff_are_isolated(tmp_path, capsys):
    pdf = native_pdf(tmp_path / "r.pdf", "Source 1 - Book. Exact rule unknown.")
    base = ["--workspace", str(tmp_path / "store")]
    args = [*base, "import", str(pdf), "--provider", "test", "--research-id", "RQ-example"]
    assert external_cli.main(args) == 0
    first = json.loads(capsys.readouterr().out)
    assert external_cli.main(args) == 0
    assert json.loads(capsys.readouterr().out) == first
    assert external_cli.main([*base, "leads"]) == 0
    assert json.loads(capsys.readouterr().out)["report_count"] == 1
    assert external_cli.main([*base, "handoff"]) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert not (tmp_path / "store" / "brain").exists()


def test_cli_refuses_production_workspace(capsys):
    assert external_cli.main(["--workspace", str(PROJECT_ROOT), "leads"]) == 2


def test_cli_leads_unknown_workspace_does_not_create_it(tmp_path, capsys):
    path = tmp_path / "absent"
    assert external_cli.main(["--workspace", str(path), "leads"]) == 2
    assert not path.exists()
