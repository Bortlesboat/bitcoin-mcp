# bitcoin-mcp Backlog Sweep Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address the still-open repo requests on `origin/main` and leave the repo verified from a clean isolated branch.

**Architecture:** Keep the sweep narrow and acceptance-criteria driven. Use tests to lock behavior before code changes, then update docs/config to match real functionality already present in `main`.

**Tech Stack:** Python, pytest, GitHub CLI, Markdown docs/config examples.

---

## Chunk 1: Tracking And Docs

### Task 1: Add backlog tracking surfaces

**Files:**
- Create: `tasks/todo.md`
- Create: `tasks/lessons.md`
- Create: `docs/superpowers/specs/2026-04-14-backlog-sweep-design.md`
- Create: `docs/superpowers/plans/2026-04-14-backlog-sweep.md`

- [x] Step 1: Create repo-local tracking and plan files for this sweep.
- [ ] Step 2: Keep `tasks/todo.md` updated as chunks complete.

### Task 2: Finish docs/config gaps already partly present on `main`

**Files:**
- Modify: `README.md`
- Verify: `examples/zed.json`

- [ ] Step 1: Add/adjust README tests or focused assertions if practical for docs-sensitive behavior.
- [ ] Step 2: Update Quick Start with a Zed section that matches `examples/zed.json`.
- [ ] Step 3: Document the `--transport` flag in the configuration/CLI docs.
- [ ] Step 4: Re-run targeted checks to ensure examples and docs stay aligned.

## Chunk 2: Low-Risk Maintenance Fixes

### Task 3: Land `py.typed` and L402 type-hint support

**Files:**
- Create: `src/bitcoin_mcp/py.typed`
- Modify: `src/bitcoin_mcp/l402_client.py`
- Modify: `pyproject.toml` if packaging needs explicit inclusion

- [ ] Step 1: Write or adapt a failing verification for the missing marker/annotations.
- [ ] Step 2: Add the marker and missing return types.
- [ ] Step 3: Run focused verification for install/type expectations.

### Task 4: Add lightweight address validation

**Files:**
- Modify: `src/bitcoin_mcp/server.py`
- Create or modify: `tests/test_server.py` or a focused validation test file

- [ ] Step 1: Add failing tests for empty, short, bad-prefix, and valid address inputs.
- [ ] Step 2: Implement lightweight prefix/length validation in the address tools.
- [ ] Step 3: Re-run the focused tests, then broader address-related tests.

## Chunk 3: Missing Test Coverage

### Task 5: Add resource coverage

**Files:**
- Modify: `tests/test_server.py`

- [ ] Step 1: Add failing tests for the untested MCP resources.
- [ ] Step 2: Implement only the test additions needed to make them pass on current behavior.
- [ ] Step 3: Run the focused resource test slice.

### Task 6: Add PSBT security and L402 client coverage

**Files:**
- Modify: `tests/conftest.py` if needed
- Create: `tests/test_psbt_security.py`
- Create: `tests/test_l402_client.py`

- [ ] Step 1: Add failing tests that cover malformed input and safety-critical paths.
- [ ] Step 2: Add any minimal fixture helpers needed for deterministic mocking.
- [ ] Step 3: Run the focused new test files, then the full suite.

## Chunk 4: Remaining Feature Gaps

### Task 7: Implement `decode_xpub`

**Files:**
- Modify: `src/bitcoin_mcp/server.py`
- Modify: `tests/test_server.py`

- [ ] Step 1: Add or adapt failing tests for private-key rejection, descriptor construction, range limits, and metadata output.
- [ ] Step 2: Implement `decode_xpub` with explicit public-key-only validation and RPC-backed derivation.
- [ ] Step 3: Verify the focused decode_xpub tests and the full suite.

### Task 8: Implement `get_address_transactions`

**Files:**
- Modify: `src/bitcoin_mcp/server.py`
- Modify: `tests/test_server.py`

- [ ] Step 1: Add failing tests for successful paginated history and error handling.
- [ ] Step 2: Implement the indexer-backed transaction list with sensible limit/offset handling.
- [ ] Step 3: Verify the focused tests and the full suite.

## Chunk 5: Final Verification

### Task 9: Verify and summarize tracker follow-up

**Files:**
- Modify: `tasks/todo.md`
- Modify: `tasks/lessons.md`

- [ ] Step 1: Run the full repo-native verification command.
- [ ] Step 2: Update task tracking with what landed and any remaining maintainer actions.
- [ ] Step 3: Summarize which open issues/PRs are now superseded or still need GitHub-side cleanup.
