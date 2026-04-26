# Codex Switcher Invalid Account Handling Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show all accounts in `--list` with explicit health status, keep `--best` restricted to normal accounts, and add a manual `--delete` command so users can remove bad saved accounts themselves.

**Architecture:** Extend the live account row pipeline with an explicit account-status classifier that labels each row as `ok`, `exhausted`, `reauth`, or `unknown_usage`. `--list` surfaces all rows with that status, `--best` filters to `ok` rows only, and the delete path removes the saved auth snapshot plus matching usage cache while leaving the current live auth file untouched.

**Tech Stack:** Python 3, argparse, pathlib, json, unittest/pytest-style monkeypatch tests

---

### Task 1: Lock the behavior with tests

**Files:**
- Create: `tests/test_codex_switcher.py`
- Modify: `codex_switcher.py`
- Test: `tests/test_codex_switcher.py`

**Step 1: Write the failing tests**

Add tests for:
- `run_best_command(..., json_output=True)` skipping invalid or exhausted accounts and choosing the first healthy one
- `run_list_command(..., json_output=True)` returning all accounts with explicit status labels
- `run_delete_command(..., json_output=True)` deleting saved auth + usage cache
- `run_delete_command(..., json_output=True)` rejecting deletion of the current account

**Step 2: Run test to verify it fails**

Run: `pytest -q tests/test_codex_switcher.py`
Expected: FAIL because filtering and delete command do not exist yet

### Task 2: Implement the minimal account-health filter

**Files:**
- Modify: `codex_switcher.py`
- Test: `tests/test_codex_switcher.py`

**Step 1: Add helpers for machine-facing health checks**

Implement small helpers to:
- identify missing/unknown usage data
- identify invalid token refresh states such as `reauth`
- compute a stable status code/text pair for each row
- filter rows for `--best`

**Step 2: Wire filtering into JSON/list/best commands**

Make `run_list_command` return all rows with status metadata, and make `run_best_command` operate only on healthy rows.

**Step 3: Run targeted tests**

Run: `pytest -q tests/test_codex_switcher.py -k 'best or list'`
Expected: PASS

### Task 3: Implement manual deletion

**Files:**
- Modify: `codex_switcher.py`
- Test: `tests/test_codex_switcher.py`

**Step 1: Add CLI support**

Add `--delete SELECTOR` to the non-interactive parser and command dispatcher.

**Step 2: Add minimal delete logic**

Delete:
- saved auth snapshot under `accounts/`
- matching usage cache file

Reject:
- deleting the current account row
- deleting rows without a saved snapshot

**Step 3: Run targeted tests**

Run: `pytest -q tests/test_codex_switcher.py -k 'delete'`
Expected: PASS

### Task 4: Verify the end-to-end behavior

**Files:**
- Modify: `codex_switcher.py`
- Test: `tests/test_codex_switcher.py`

**Step 1: Run the full focused test file**

Run: `pytest -q tests/test_codex_switcher.py`
Expected: PASS

**Step 2: Check CLI output shape**

Run:
- `python codex_switcher.py --list --json`
- `python codex_switcher.py --best --json`
- `python codex_switcher.py --help`

Expected:
- invalid accounts are visible in list output with explicit status labels
- best output only contains healthy accounts
- help includes `--delete`
