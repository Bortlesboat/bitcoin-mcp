# bitcoin-mcp Backlog Sweep Design

**Goal**

Reduce repo backlog drift by landing the still-missing work behind open issues, folding in the safe parts of existing open PRs, and leaving the tracker in a state where remaining items correspond to real unmet work.

**Scope**

- Close documentation/config gaps already partially present on `main`.
- Land low-risk maintenance fixes that already have clear issue acceptance criteria.
- Add missing tests around security- and reliability-sensitive paths.
- Implement the two remaining open feature requests on `main`: `decode_xpub` and `get_address_transactions`.

**Non-goals**

- Rewriting the project structure.
- Touching the maintainer's dirty local checkout.
- Blindly merging contributor PRs without validating behavior locally.

**Approach**

Work in an isolated branch off `origin/main`, reusing the current codebase patterns and issue acceptance criteria. Favor small, reviewable changes with tests first for each behavior change. Where open PRs are stacked or contain unrelated files, port only the clean, intended behavior into the sweep branch.

**Risk Notes**

- `decode_xpub` touches key-handling semantics, so private-key rejection messaging must be explicit and tested.
- Address validation must stay lightweight and not reject clearly valid prefixes already accepted by the repo.
- New docs should reflect the actual `main` behavior rather than stale or stacked PR branches.
