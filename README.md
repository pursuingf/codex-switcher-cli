# codex-switcher-cli

Local Codex account switching helper with quota inspection, saved-account deletion, and login-state migration.

## Commands

```bash
codex-switcher --list
codex-switcher --list --json
codex-switcher --best
codex-switcher --best --json
codex-switcher --switch best
codex-switcher --delete 1
codex-switcher --save-current
codex-switcher --refresh
```

## Backup Migration

Export login state and shared config:

```bash
codex-switcher --export
codex-switcher --export ./codex-migration.zip
```

Import on another server:

```bash
codex-switcher --import ./codex-migration.zip
```

The migration archive includes:

- `~/.codex/auth.json`
- `~/codex-switcher/accounts/auth_*.json`
- filtered `~/.codex/config.toml`
- filtered Codex Switcher related snippets from `~/.bashrc`

It excludes local sessions, usage cache, runtime files, backups, and `[projects]` / `[projects."/local/path"]` sections from `config.toml`.

For `.bashrc`, only Codex Switcher related shell snippets are migrated, such as `alias csw`, the `codex()` wrapper, and related `clashon` / proxy defaults when present. The importer appends them to the end of the target `.bashrc` between `======codexSwitcher======` separator lines instead of replacing the whole file.

Migration archives contain login credentials. Treat them like tokens and do not commit or share them.

## Development Checks

```bash
python3 -m pytest tests/test_codex_switcher.py -q
python3 -m py_compile codex_switcher.py codex-switcher.py
python3 codex_switcher.py --help
```
