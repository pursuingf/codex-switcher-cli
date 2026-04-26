# Codex Switcher Ranking Threshold Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make account ranking favor durable weekly headroom by introducing a `20%` weekly threshold tier while keeping exhausted or invalid accounts out of `--best`.

**Architecture:** Replace the current simple hourly-first sort with a tiered ranking key shared by `--list`, `--best`, and selector resolution. Tier 1 contains healthy accounts with `weekly_remaining_pct >= 20`, tier 2 contains healthy accounts with `0 < weekly_remaining_pct < 20`, and tier 3 contains everything else. Within each tier, sort by weekly remaining percent first, then hourly remaining percent, then email for deterministic output.

**Tech Stack:** Python 3, argparse, pathlib, pytest monkeypatch tests

---

### Task 1: Lock the new ranking behavior with tests

**Files:**
- Modify: `tests/test_codex_switcher.py`
- Modify: `codex_switcher.py`

**Step 1: Write the failing tests**

Add tests for:
- `--best` preferring a healthy account above the weekly threshold over a high-hourly account below the threshold
- `--list` placing low-weekly healthy accounts after threshold-safe healthy accounts
- `--list` still placing threshold-degraded healthy accounts ahead of invalid accounts

**Step 2: Run targeted tests**

Run: `pytest -q tests/test_codex_switcher.py -k 'ranking or threshold or best_command'`
Expected: FAIL before implementation

### Task 2: Implement the tiered ranking key

**Files:**
- Modify: `codex_switcher.py`
- Modify: `tests/test_codex_switcher.py`

**Step 1: Add a named threshold constant**

Introduce a single weekly threshold constant set to `20`.

**Step 2: Add ranking-tier helpers**

Implement helpers for:
- healthy-above-threshold tier
- healthy-below-threshold tier
- invalid/exhausted tier

**Step 3: Replace the sort key**

Update the main account ranking function so all selector-based flows share the same ordering.

### Task 3: Verify the new behavior

**Files:**
- Modify: `codex_switcher.py`
- Modify: `tests/test_codex_switcher.py`

**Step 1: Run the focused test file**

Run: `pytest -q tests/test_codex_switcher.py`
Expected: PASS

**Step 2: Spot-check the real CLI**

Run:
- `python codex_switcher.py --list --json`
- `python codex_switcher.py --best --json`

Expected:
- weekly headroom dominates ranking among healthy accounts
- low-weekly accounts are pushed behind threshold-safe healthy accounts
- `--best` never returns invalid or exhausted accounts
