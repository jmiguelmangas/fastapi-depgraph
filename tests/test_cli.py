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
    assert "Dependencies shared across routes:" in out
    assert "get_settings" in out
    assert "Dependencies with use_cache=False:" in out
    assert "get_request_id" in out


def test_show_shared_flag_reports_none_when_nothing_shared(capsys):
    main(["show", "tests.fixtures.router_app:app", "--shared"])
    out = capsys.readouterr().out
    assert "(none)" in out


def test_export_mermaid(capsys):
    main(["export", "tests.fixtures.sample_app:app", "--format", "mermaid"])
    out = capsys.readouterr().out
    assert out.startswith("graph TD;")


def test_malformed_app_path_exits_with_clear_message():
    with pytest.raises(SystemExit, match="module:app"):
        main(["show", "no-colon-here"])


def test_missing_module_exits_with_clear_message():
    with pytest.raises(SystemExit, match="Could not import"):
        main(["show", "definitely_not_a_real_module:app"])


def test_missing_attribute_exits_with_clear_message():
    with pytest.raises(SystemExit, match="Could not find"):
        main(["show", "tests.fixtures.sample_app:nonexistent_app"])
