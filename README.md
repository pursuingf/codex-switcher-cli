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

It excludes local sessions, usage cache, runtime files, backups, and `[projects]` / `[projects."/local/path"]` sections from `config.toml`.

Migration archives contain login credentials. Treat them like tokens and do not commit or share them.

## Development Checks

```bash
python3 -m pytest tests/test_codex_switcher.py -q
python3 -m py_compile codex_switcher.py codex-switcher.py
python3 codex_switcher.py --help
```
