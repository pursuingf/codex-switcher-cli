import io
import json
import sys
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import codex_switcher as cs


def capture_json_output(func, *args, **kwargs):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = func(*args, **kwargs)
    return exit_code, json.loads(buffer.getvalue())


def make_row(
    email: str,
    *,
    hourly_remaining: str = "50",
    weekly_remaining: str = "50",
    hourly_remaining_pct: int | None = None,
    weekly_remaining_pct: int | None = None,
    refresh_status: str = "fresh",
    is_current: bool = False,
    switch_path: str | None = None,
    identity: str | None = None,
    account_id: str = "acct-1",
):
    if hourly_remaining_pct is None:
        try:
            hourly_remaining_pct = int(hourly_remaining)
        except (TypeError, ValueError):
            hourly_remaining_pct = 100
    if weekly_remaining_pct is None:
        try:
            weekly_remaining_pct = int(weekly_remaining)
        except (TypeError, ValueError):
            weekly_remaining_pct = 100
    return {
        "email": email,
        "plan_type": "plus",
        "hourly_remaining": hourly_remaining,
        "weekly_remaining": weekly_remaining,
        "hourly_percent": max(0, 100 - hourly_remaining_pct),
        "weekly_percent": max(0, 100 - weekly_remaining_pct),
        "reset_at_hourly": 0,
        "reset_at_weekly": 0,
        "refresh_status": refresh_status,
        "is_current": is_current,
        "is_saved": bool(switch_path),
        "identity": identity or f"user::{email}",
        "switch_path": switch_path,
        "account_id": account_id,
        "workspace_title": "Personal",
        "workspace_id": "org-test",
        "workspace_role": "owner",
        "workspace_display": "Personal",
    }


def test_run_best_command_skips_invalid_accounts(monkeypatch):
    rows = [
        make_row(
            "bad@example.com",
            hourly_remaining="80",
            weekly_remaining="80",
            refresh_status="reauth",
            switch_path="/tmp/auth_bad.json",
        ),
        make_row(
            "good@example.com",
            hourly_remaining="40",
            weekly_remaining="40",
            refresh_status="fresh",
            switch_path="/tmp/auth_good.json",
        ),
    ]
    monkeypatch.setattr(cs, "load_live_account_rows", lambda show_progress=False: rows)

    exit_code, payload = capture_json_output(cs.run_best_command, True)

    assert exit_code == 0
    assert payload["email"] == "good@example.com"


def test_run_list_command_marks_invalid_accounts(monkeypatch):
    rows = [
        make_row(
            "bad@example.com",
            hourly_remaining="80",
            weekly_remaining="80",
            refresh_status="reauth",
            switch_path="/tmp/auth_bad.json",
        ),
        make_row(
            "good@example.com",
            hourly_remaining="40",
            weekly_remaining="40",
            refresh_status="fresh",
            switch_path="/tmp/auth_good.json",
        ),
    ]
    monkeypatch.setattr(cs, "load_live_account_rows", lambda show_progress=False: rows)

    exit_code, payload = capture_json_output(cs.run_list_command, True)

    assert exit_code == 0
    assert [item["email"] for item in payload] == ["good@example.com", "bad@example.com"]
    assert payload[0]["status"] == "ok"
    assert payload[0]["status_text"] == "正常"
    assert payload[1]["status"] == "reauth"
    assert payload[1]["status_text"] == "auth token失效"


def test_run_best_command_skips_exhausted_accounts(monkeypatch):
    rows = [
        make_row(
            "empty@example.com",
            hourly_remaining="80",
            weekly_remaining="0",
            refresh_status="fresh",
            switch_path="/tmp/auth_empty.json",
        ),
        make_row(
            "usable@example.com",
            hourly_remaining="40",
            weekly_remaining="10",
            refresh_status="fresh",
            switch_path="/tmp/auth_usable.json",
        ),
    ]
    monkeypatch.setattr(cs, "load_live_account_rows", lambda show_progress=False: rows)

    exit_code, payload = capture_json_output(cs.run_best_command, True)

    assert exit_code == 0
    assert payload["email"] == "usable@example.com"


def test_run_best_command_prefers_weekly_threshold_safe_accounts(monkeypatch):
    rows = [
        make_row(
            "low-weekly@example.com",
            hourly_remaining="80",
            weekly_remaining="10",
            refresh_status="fresh",
            switch_path="/tmp/auth_low_weekly.json",
        ),
        make_row(
            "threshold-safe@example.com",
            hourly_remaining="40",
            weekly_remaining="30",
            refresh_status="fresh",
            switch_path="/tmp/auth_threshold_safe.json",
        ),
    ]
    monkeypatch.setattr(cs, "load_live_account_rows", lambda show_progress=False: rows)

    exit_code, payload = capture_json_output(cs.run_best_command, True)

    assert exit_code == 0
    assert payload["email"] == "threshold-safe@example.com"


def test_run_list_command_marks_exhausted_accounts(monkeypatch):
    rows = [
        make_row(
            "empty@example.com",
            hourly_remaining="80",
            weekly_remaining="0",
            refresh_status="fresh",
            switch_path="/tmp/auth_empty.json",
        ),
        make_row(
            "usable@example.com",
            hourly_remaining="40",
            weekly_remaining="10",
            refresh_status="fresh",
            switch_path="/tmp/auth_usable.json",
        ),
    ]
    monkeypatch.setattr(cs, "load_live_account_rows", lambda show_progress=False: rows)

    exit_code, payload = capture_json_output(cs.run_list_command, True)

    assert exit_code == 0
    assert [item["email"] for item in payload] == ["usable@example.com", "empty@example.com"]
    assert payload[0]["status"] == "ok"
    assert payload[0]["status_text"] == "正常"
    assert payload[1]["status"] == "exhausted"
    assert payload[1]["status_text"] == "额度耗尽"


def test_run_list_command_marks_unknown_usage(monkeypatch):
    rows = [
        make_row(
            "unknown@example.com",
            hourly_remaining="?",
            weekly_remaining="?",
            refresh_status="cached",
            switch_path="/tmp/auth_unknown.json",
        ),
        make_row(
            "usable@example.com",
            hourly_remaining="40",
            weekly_remaining="10",
            refresh_status="fresh",
            switch_path="/tmp/auth_usable.json",
        ),
    ]
    monkeypatch.setattr(cs, "load_live_account_rows", lambda show_progress=False: rows)

    exit_code, payload = capture_json_output(cs.run_list_command, True)

    assert exit_code == 0
    assert [item["email"] for item in payload] == ["usable@example.com", "unknown@example.com"]
    assert payload[0]["status"] == "ok"
    assert payload[1]["status"] == "unknown_usage"
    assert payload[1]["status_text"] == "额度未知"


def test_run_list_command_pushes_low_weekly_accounts_behind_threshold_safe_accounts(monkeypatch):
    rows = [
        make_row(
            "low-weekly@example.com",
            hourly_remaining="80",
            weekly_remaining="10",
            refresh_status="fresh",
            switch_path="/tmp/auth_low_weekly.json",
        ),
        make_row(
            "threshold-safe@example.com",
            hourly_remaining="40",
            weekly_remaining="30",
            refresh_status="fresh",
            switch_path="/tmp/auth_threshold_safe.json",
        ),
    ]
    monkeypatch.setattr(cs, "load_live_account_rows", lambda show_progress=False: rows)

    exit_code, payload = capture_json_output(cs.run_list_command, True)

    assert exit_code == 0
    assert [item["email"] for item in payload] == [
        "threshold-safe@example.com",
        "low-weekly@example.com",
    ]


def test_run_list_command_keeps_low_weekly_accounts_ahead_of_invalid_accounts(monkeypatch):
    rows = [
        make_row(
            "invalid@example.com",
            hourly_remaining="80",
            weekly_remaining="80",
            refresh_status="reauth",
            switch_path="/tmp/auth_invalid.json",
        ),
        make_row(
            "low-weekly@example.com",
            hourly_remaining="80",
            weekly_remaining="10",
            refresh_status="fresh",
            switch_path="/tmp/auth_low_weekly.json",
        ),
    ]
    monkeypatch.setattr(cs, "load_live_account_rows", lambda show_progress=False: rows)

    exit_code, payload = capture_json_output(cs.run_list_command, True)

    assert exit_code == 0
    assert [item["email"] for item in payload] == [
        "low-weekly@example.com",
        "invalid@example.com",
    ]


def test_parser_accepts_delete_selector():
    parser = cs.build_arg_parser()

    args = parser.parse_args(["--delete", "bad@example.com"])

    assert args.delete == "bad@example.com"


def test_run_delete_command_removes_saved_auth_and_usage_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(cs, "get_home_dir", lambda: tmp_path)

    accounts_dir = cs.get_accounts_dir()
    accounts_dir.mkdir(parents=True, exist_ok=True)
    auth_path = accounts_dir / "auth_bad_example_com.json"
    auth_path.write_text("{}", encoding="utf-8")

    identity = "user-bad::acct-bad"
    cache_path = cs.get_usage_cache_file("bad@example.com", "acct-bad", identity)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text("{}", encoding="utf-8")

    rows = [
        make_row(
            "bad@example.com",
            identity=identity,
            account_id="acct-bad",
            switch_path=str(auth_path),
        )
    ]
    monkeypatch.setattr(cs, "load_live_account_rows", lambda show_progress=False: rows)

    exit_code, payload = capture_json_output(cs.run_delete_command, "bad@example.com", True)

    assert exit_code == 0
    assert payload["ok"] is True
    assert not auth_path.exists()
    assert not cache_path.exists()


def test_run_delete_command_supports_rank_selector(monkeypatch, tmp_path):
    monkeypatch.setattr(cs, "get_home_dir", lambda: tmp_path)

    accounts_dir = cs.get_accounts_dir()
    accounts_dir.mkdir(parents=True, exist_ok=True)
    auth_top = accounts_dir / "auth_top.json"
    auth_other = accounts_dir / "auth_other.json"
    auth_top.write_text("{}", encoding="utf-8")
    auth_other.write_text("{}", encoding="utf-8")

    rows = [
        make_row(
            "top@example.com",
            identity="id-top",
            account_id="acct-top",
            hourly_remaining="80",
            weekly_remaining="80",
            switch_path=str(auth_top),
        ),
        make_row(
            "other@example.com",
            identity="id-other",
            account_id="acct-other",
            hourly_remaining="40",
            weekly_remaining="40",
            switch_path=str(auth_other),
        ),
    ]
    monkeypatch.setattr(cs, "load_live_account_rows", lambda show_progress=False: rows)

    exit_code, payload = capture_json_output(cs.run_delete_command, "1", True)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["account"]["email"] == "top@example.com"
    assert not auth_top.exists()
    assert auth_other.exists()


def test_run_delete_command_rejects_current_account(monkeypatch):
    rows = [
        make_row(
            "current@example.com",
            is_current=True,
            switch_path="/tmp/auth_current.json",
        )
    ]
    monkeypatch.setattr(cs, "load_live_account_rows", lambda show_progress=False: rows)

    exit_code, payload = capture_json_output(cs.run_delete_command, "current@example.com", True)

    assert exit_code == 1
    assert payload["ok"] is False
    assert "当前" in payload["error"]


def test_apply_default_proxy_env_sets_clash_proxy_vars(monkeypatch):
    for key in [
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
    ]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CLASH_HOST", "127.0.0.1")
    monkeypatch.setenv("CLASH_MIXED_PORT", "7897")

    cs.apply_default_proxy_env()

    assert cs.os.environ["http_proxy"] == "http://127.0.0.1:7897"
    assert cs.os.environ["https_proxy"] == "http://127.0.0.1:7897"
    assert cs.os.environ["all_proxy"] == "socks5://127.0.0.1:7897"
    assert cs.os.environ["HTTP_PROXY"] == "http://127.0.0.1:7897"
    assert cs.os.environ["HTTPS_PROXY"] == "http://127.0.0.1:7897"
    assert cs.os.environ["ALL_PROXY"] == "socks5://127.0.0.1:7897"


def test_main_applies_proxy_env_and_does_not_clear_on_exit(monkeypatch, tmp_path):
    monkeypatch.setattr(cs, "get_home_dir", lambda: tmp_path)
    for key in [
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
    ]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CLASH_HOST", "127.0.0.1")
    monkeypatch.setenv("CLASH_MIXED_PORT", "7897")

    clear_calls = []
    seen_env = {}

    class FakeParser:
        def parse_args(self):
            return SimpleNamespace(
                list=False,
                json=False,
                best=False,
                switch=None,
                delete=None,
                save_current=None,
                refresh=False,
            )

    def fake_view_all_accounts():
        seen_env["http_proxy"] = cs.os.environ.get("http_proxy")
        seen_env["https_proxy"] = cs.os.environ.get("https_proxy")
        seen_env["all_proxy"] = cs.os.environ.get("all_proxy")

    monkeypatch.setattr(cs, "build_arg_parser", lambda: FakeParser())
    monkeypatch.setattr(cs, "view_all_accounts", fake_view_all_accounts)
    monkeypatch.setattr(cs, "clear_screen", lambda: clear_calls.append("clear"))

    cs.main()

    assert seen_env == {
        "http_proxy": "http://127.0.0.1:7897",
        "https_proxy": "http://127.0.0.1:7897",
        "all_proxy": "socks5://127.0.0.1:7897",
    }
    assert clear_calls == []


def test_print_view_all_actions_includes_delete_entry(capsys):
    cs.print_view_all_actions([])

    captured = capsys.readouterr().out

    assert "[r]" in captured
    assert "刷新账号状态" in captured
    assert "[d]" in captured
    assert "删除账号" in captured
    assert "[Enter]" not in captured


def test_delete_account_from_view_removes_selected_saved_account(monkeypatch, tmp_path):
    monkeypatch.setattr(cs, "get_home_dir", lambda: tmp_path)
    monkeypatch.setattr(cs, "clear_screen", lambda: None)
    monkeypatch.setattr(cs, "print_header", lambda: None)

    accounts_dir = cs.get_accounts_dir()
    accounts_dir.mkdir(parents=True, exist_ok=True)
    auth_path = accounts_dir / "auth_delete_me.json"
    auth_path.write_text("{}", encoding="utf-8")

    rows = [
        make_row(
            "delete-me@example.com",
            identity="id-delete",
            account_id="acct-delete",
            switch_path=str(auth_path),
        ),
    ]
    monkeypatch.setattr(cs, "load_live_account_rows", lambda show_progress=True: rows)

    answers = iter(["1", "y", "0"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    cs.delete_account_from_view()

    assert not auth_path.exists()


def test_print_delete_actions_hides_enter_refresh_prompt(capsys):
    cs.print_delete_actions()

    captured = capsys.readouterr().out

    assert "[Enter]" not in captured


def test_view_all_accounts_does_not_clear_screen_on_entry(monkeypatch):
    clear_calls = []
    monkeypatch.setattr(cs, "clear_screen", lambda: clear_calls.append("clear"))
    monkeypatch.setattr(cs, "print_header", lambda: None)
    monkeypatch.setattr(cs, "load_live_account_rows", lambda show_progress=True: [])
    monkeypatch.setattr("builtins.input", lambda prompt="": "0")

    cs.view_all_accounts()

    assert clear_calls == []


def test_view_all_accounts_supports_r_refresh(monkeypatch):
    load_calls = []
    monkeypatch.setattr(cs, "print_header", lambda: None)
    monkeypatch.setattr(
        cs,
        "load_live_account_rows",
        lambda show_progress=True: load_calls.append(show_progress) or [],
    )

    answers = iter(["r", "0"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    cs.view_all_accounts()

    assert load_calls == [True, True]


def test_delete_account_from_view_does_not_clear_screen_on_entry(monkeypatch):
    clear_calls = []
    monkeypatch.setattr(cs, "clear_screen", lambda: clear_calls.append("clear"))
    monkeypatch.setattr(cs, "print_header", lambda: None)
    monkeypatch.setattr(cs, "load_live_account_rows", lambda show_progress=True: [])
    monkeypatch.setattr("builtins.input", lambda prompt="": "0")

    cs.delete_account_from_view()

    assert clear_calls == []


def test_filter_migratable_config_removes_projects_sections():
    source = '''
model = "gpt-5.4"
approval_policy = "never"

[profiles.default]
model = "gpt-5.4"

[projects."/data/pxd-team/workspace/fyh/evolve_ctf_agent"]
trust_level = "trusted"

[mcp_servers.local]
command = "tool"
'''

    result = cs.filter_migratable_config(source)

    assert 'model = "gpt-5.4"' in result
    assert "[profiles.default]" in result
    assert "[mcp_servers.local]" in result
    assert "[projects." not in result
    assert "evolve_ctf_agent" not in result


def test_merge_migratable_config_preserves_target_projects():
    target = '''
model = "old"

[projects."/target/server/project"]
trust_level = "trusted"
'''
    incoming = '''
model = "new"

[projects."/source/server/project"]
trust_level = "trusted"

[profiles.default]
model = "gpt-5.4"
'''

    result = cs.merge_migratable_config(target, incoming)

    assert 'model = "new"' in result
    assert "[profiles.default]" in result
    assert '[projects."/target/server/project"]' in result
    assert '[projects."/source/server/project"]' not in result


def test_export_migration_archive_contains_login_state_and_filtered_config(tmp_path, monkeypatch):
    codex_dir = tmp_path / ".codex"
    switcher_dir = tmp_path / "codex-switcher"
    accounts_dir = switcher_dir / "accounts"
    codex_dir.mkdir()
    accounts_dir.mkdir(parents=True)
    (codex_dir / "auth.json").write_text('{"tokens": {"id_token": "x"}}\n', encoding="utf-8")
    (codex_dir / "config.toml").write_text(
        'model = "gpt-5.4"\n\n[projects."/old/path"]\ntrust_level = "trusted"\n',
        encoding="utf-8",
    )
    (accounts_dir / "auth_saved.json").write_text('{"saved": true}\n', encoding="utf-8")
    archive_path = tmp_path / "migration.zip"

    monkeypatch.setattr(cs, "get_codex_config_dir", lambda: codex_dir)
    monkeypatch.setattr(cs, "get_auth_file", lambda: codex_dir / "auth.json")
    monkeypatch.setattr(cs, "get_switcher_dir", lambda: switcher_dir)
    monkeypatch.setattr(cs, "get_accounts_dir", lambda: accounts_dir)

    result = cs.export_migration_archive(str(archive_path))

    assert result["ok"] is True
    with zipfile.ZipFile(archive_path) as zf:
        names = set(zf.namelist())
        assert "manifest.json" in names
        assert "codex/auth.json" in names
        assert "codex/config.toml" in names
        assert "codex-switcher/accounts/auth_saved.json" in names
        config = zf.read("codex/config.toml").decode("utf-8")
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
    assert "[projects." not in config
    assert manifest["version"] == 1


def test_import_migration_archive_restores_auth_and_preserves_target_projects(tmp_path, monkeypatch):
    codex_dir = tmp_path / ".codex"
    switcher_dir = tmp_path / "codex-switcher"
    accounts_dir = switcher_dir / "accounts"
    codex_dir.mkdir()
    accounts_dir.mkdir(parents=True)
    (codex_dir / "config.toml").write_text(
        'model = "old"\n\n[projects."/target/path"]\ntrust_level = "trusted"\n',
        encoding="utf-8",
    )
    archive_path = tmp_path / "migration.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"version": 1}))
        zf.writestr("codex/auth.json", '{"tokens": {"id_token": "new"}}\n')
        zf.writestr("codex/config.toml", 'model = "new"\n\n[profiles.default]\nmodel = "gpt-5.4"\n')
        zf.writestr("codex-switcher/accounts/auth_saved.json", '{"saved": true}\n')

    monkeypatch.setattr(cs, "get_codex_config_dir", lambda: codex_dir)
    monkeypatch.setattr(cs, "get_auth_file", lambda: codex_dir / "auth.json")
    monkeypatch.setattr(cs, "get_switcher_dir", lambda: switcher_dir)
    monkeypatch.setattr(cs, "get_accounts_dir", lambda: accounts_dir)

    result = cs.import_migration_archive(str(archive_path))

    assert result["ok"] is True
    assert (codex_dir / "auth.json").read_text(encoding="utf-8") == '{"tokens": {"id_token": "new"}}\n'
    config = (codex_dir / "config.toml").read_text(encoding="utf-8")
    assert 'model = "new"' in config
    assert "[profiles.default]" in config
    assert '[projects."/target/path"]' in config
    assert (accounts_dir / "auth_saved.json").exists()
    assert Path(result["backup_dir"]).exists()


def test_arg_parser_accepts_export_import_and_existing_delete_flag():
    parser = cs.build_arg_parser()

    export_args = parser.parse_args(["--export", "backup.zip", "--json"])
    import_args = parser.parse_args(["--import", "backup.zip", "--json"])
    delete_args = parser.parse_args(["--delete", "1", "--json"])

    assert export_args.export_path == "backup.zip"
    assert export_args.json is True
    assert import_args.import_path == "backup.zip"
    assert import_args.json is True
    assert delete_args.delete == "1"
    assert delete_args.json is True


def test_build_migratable_bashrc_fragment_keeps_codex_related_shell_only():
    source = '''
export CLASH_HOST="${CLASH_HOST:-0.0.0.0}"
export CLASH_MIXED_PORT="${CLASH_MIXED_PORT:-7890}"

clashon() {
  echo "proxy on"
}

clashoff() {
  echo "proxy off"
}

# Codex Switcher
export PATH="$PATH:/home/pgroup/.local/bin"
alias csw="codex-switcher"

codex() {
  clashon
  codex-switcher --switch best > /dev/null
  command codex "$@"
}

claude() {
  echo "do not migrate"
}
'''

    fragment = cs.build_migratable_bashrc_fragment(source)

    assert "CLASH_HOST" in fragment
    assert "clashon()" in fragment
    assert 'alias csw="codex-switcher"' in fragment
    assert "codex-switcher --switch best" in fragment
    assert "claude()" not in fragment
    assert "do not migrate" not in fragment


def test_apply_bashrc_migration_replaces_managed_block():
    target = '''
export KEEP_ME=1

# Codex Switcher Migration START
old content
# Codex Switcher Migration END
'''
    incoming = 'alias csw="codex-switcher"\n'

    result = cs.apply_bashrc_migration(target, incoming)

    assert "export KEEP_ME=1" in result
    assert "old content" not in result
    assert 'alias csw="codex-switcher"' in result
    assert result.count("Codex Switcher Migration START") == 1


def test_export_migration_archive_includes_filtered_bashrc_fragment(tmp_path, monkeypatch):
    codex_dir = tmp_path / ".codex"
    switcher_dir = tmp_path / "codex-switcher"
    accounts_dir = switcher_dir / "accounts"
    bashrc_path = tmp_path / ".bashrc"
    codex_dir.mkdir()
    accounts_dir.mkdir(parents=True)
    (codex_dir / "auth.json").write_text('{"tokens": {"id_token": "x"}}\n', encoding="utf-8")
    bashrc_path.write_text(
        '# Codex Switcher\nalias csw="codex-switcher"\n\nclaude() { echo no; }\n',
        encoding="utf-8",
    )
    archive_path = tmp_path / "migration.zip"

    monkeypatch.setattr(cs, "get_codex_config_dir", lambda: codex_dir)
    monkeypatch.setattr(cs, "get_auth_file", lambda: codex_dir / "auth.json")
    monkeypatch.setattr(cs, "get_switcher_dir", lambda: switcher_dir)
    monkeypatch.setattr(cs, "get_accounts_dir", lambda: accounts_dir)
    monkeypatch.setattr(cs, "get_bashrc_file", lambda: bashrc_path)

    result = cs.export_migration_archive(str(archive_path))

    assert result["ok"] is True
    with zipfile.ZipFile(archive_path) as zf:
        fragment = zf.read("shell/bashrc.codex-switcher.sh").decode("utf-8")
    assert 'alias csw="codex-switcher"' in fragment
    assert "claude" not in fragment


def test_import_migration_archive_applies_bashrc_fragment(tmp_path, monkeypatch):
    codex_dir = tmp_path / ".codex"
    switcher_dir = tmp_path / "codex-switcher"
    accounts_dir = switcher_dir / "accounts"
    bashrc_path = tmp_path / ".bashrc"
    codex_dir.mkdir()
    accounts_dir.mkdir(parents=True)
    bashrc_path.write_text("export KEEP_ME=1\n", encoding="utf-8")
    archive_path = tmp_path / "migration.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"version": 1}))
        zf.writestr("shell/bashrc.codex-switcher.sh", 'alias csw="codex-switcher"\n')

    monkeypatch.setattr(cs, "get_codex_config_dir", lambda: codex_dir)
    monkeypatch.setattr(cs, "get_auth_file", lambda: codex_dir / "auth.json")
    monkeypatch.setattr(cs, "get_switcher_dir", lambda: switcher_dir)
    monkeypatch.setattr(cs, "get_accounts_dir", lambda: accounts_dir)
    monkeypatch.setattr(cs, "get_bashrc_file", lambda: bashrc_path)

    result = cs.import_migration_archive(str(archive_path))

    assert result["ok"] is True
    bashrc = bashrc_path.read_text(encoding="utf-8")
    assert "export KEEP_ME=1" in bashrc
    assert "Codex Switcher Migration START" in bashrc
    assert 'alias csw="codex-switcher"' in bashrc
