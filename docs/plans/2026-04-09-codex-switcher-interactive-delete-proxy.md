# Codex Switcher Interactive Delete And Proxy Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make interactive `codex-switcher` sessions auto-apply proxy environment variables, add a dedicated delete page in the main view, and stop clearing the terminal on exit.

**Architecture:** Add a small startup helper that derives proxy variables from `CLASH_HOST` and `CLASH_MIXED_PORT` into both lowercase and uppercase proxy env vars before any interactive or non-interactive action runs. Extend the main interactive account view with a `d` action that opens a dedicated delete page backed by the existing delete helpers, while keeping `--delete` intact for non-interactive use. Remove the final exit-time `clear_screen()` so the last page stays visible after quitting.

**Tech Stack:** Python 3, argparse, pathlib, os.environ, pytest monkeypatch tests

---

### Task 1: Lock down startup proxy behavior

**Files:**
- Modify: `codex_switcher.py`
- Modify: `tests/test_codex_switcher.py`

**Step 1: Write the failing tests**

Add tests for:
- `main()` applying proxy env vars before entering the interactive view
- startup proxy helper setting both lowercase and uppercase proxy variables from clash settings

**Step 2: Run targeted tests**

Run: `pytest -q tests/test_codex_switcher.py -k 'proxy or main'`
Expected: FAIL before implementation

### Task 2: Add a dedicated delete page to the interactive UI

**Files:**
- Modify: `codex_switcher.py`
- Modify: `tests/test_codex_switcher.py`

**Step 1: Write the failing tests**

Add tests for:
- `view_all_accounts()` showing a delete action path
- a delete-page helper deleting the selected saved account by rank

**Step 2: Implement the smallest interactive flow**

Add:
- a `d` action in the main view action panel
- a delete page with its own prompt loop
- confirmation before deletion

### Task 3: Preserve terminal contents on exit

**Files:**
- Modify: `codex_switcher.py`
- Modify: `tests/test_codex_switcher.py`

**Step 1: Write the failing test**

Add a test asserting `main()` does not call `clear_screen()` after the interactive view returns.

**Step 2: Implement the minimal exit change**

Remove only the final exit-time screen clear.

### Task 4: Verify the flow

**Files:**
- Modify: `codex_switcher.py`
- Modify: `tests/test_codex_switcher.py`

**Step 1: Run the focused test file**

Run: `pytest -q tests/test_codex_switcher.py`
Expected: PASS

**Step 2: Spot-check the CLI**

Run:
- `python codex_switcher.py --help`
- `python codex_switcher.py --list --json`

Expected:
- no regressions in CLI output
- interactive startup still works with the new action set
