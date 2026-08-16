import pytest

from fastapi_depgraph.cli import main


def test_show_prints_tree(capsys):
    main(["show", "tests.fixtures.sample_app:app"])
    out = capsys.readouterr().out
    assert "GET /me" in out
    assert "GET /items" in out


def test_show_shared_and_uncached_flags(capsys):
    main(["show", "tests.fixtures.sample_app:app", "--shared", "--uncached"])
    out = capsys.readouterr().out
    assert "Dependencias compartidas entre rutas:" in out
    assert "get_settings" in out
    assert "Dependencias con use_cache=False:" in out
    assert "get_request_id" in out


def test_show_shared_flag_reports_none_when_nothing_shared(capsys):
    main(["show", "tests.fixtures.router_app:app", "--shared"])
    out = capsys.readouterr().out
    assert "(ninguna)" in out


def test_export_mermaid(capsys):
    main(["export", "tests.fixtures.sample_app:app", "--format", "mermaid"])
    out = capsys.readouterr().out
    assert out.startswith("graph TD;")


def test_malformed_app_path_exits_with_clear_message():
    with pytest.raises(SystemExit, match="modulo:app"):
        main(["show", "sin-dos-puntos"])


def test_missing_module_exits_with_clear_message():
    with pytest.raises(SystemExit, match="No se pudo importar"):
        main(["show", "modulo_que_no_existe_seguro:app"])


def test_missing_attribute_exits_with_clear_message():
    with pytest.raises(SystemExit, match="No se encontró"):
        main(["show", "tests.fixtures.sample_app:app_que_no_existe"])
