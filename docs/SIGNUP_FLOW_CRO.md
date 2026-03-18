# Signup Flow CRO — bitcoin-mcp → Satoshi API

*Created: 2026-03-17*

---

## Current Funnel (Broken)

```
PyPI page (256 downloads/mo)
    → pip install bitcoin-mcp
    → Use in Claude (hits Satoshi API automatically)
    → ... nothing. No registration prompt, no CTA.
```

**Problem:** 256 monthly installs, ~0 convert to Satoshi API registrations. The zero-config mode is great for UX but terrible for conversion — users get value without ever knowing they should register.

---

## Proposed Funnel

```
PyPI page → pip install → Use in Claude
    → Hits Satoshi API (anonymous, 1K req/day)
    → After 100 requests: response includes registration nudge
    → User registers for free key (10K req/day)
    → Onboarding emails kick in
    → Heavy usage → Pro upgrade
```

---

## Changes Needed

### 1. Add Registration Nudge to Satoshi API Responses (via RPC proxy)

When bitcoin-mcp users hit Satoshi API via the RPC proxy (`/api/v1/rpc`), they're anonymous. After N requests from the same IP:

Add to RPC proxy response headers:
```
X-Register-Hint: "Free API key gives you 10x more requests. Register at bitcoinsapi.com/#get-api-key"
```

**Implementation:** Track IP request count in rate limiter. After 100 anonymous RPC requests from same IP, add header.

### 2. README → Satoshi API Registration Link

Current README mentions Satoshi API but doesn't have a clear "register for free" CTA.

**Add after Quick Start section:**
```markdown
### Get More Requests (Free)

bitcoin-mcp works immediately with 1,000 requests/day (anonymous).
Register for a free API key to get 10,000/day:

1. Visit https://bitcoinsapi.com/#get-api-key
2. Set `SATOSHI_API_KEY` environment variable
3. bitcoin-mcp automatically uses your key for higher limits
```

### 3. CLI Registration Prompt

When running `bitcoin-mcp --check` and connection is via Satoshi API (not local node):

```
✓ Connected to Satoshi API (hosted)
  Rate limit: 1,000 requests/day (anonymous)

  Tip: Register for free at bitcoinsapi.com to get 10,000 req/day.
  Set SATOSHI_API_KEY env var after registration.
```

### 4. PyPI Page → README Funnel

PyPI page shows the README. Ensure the README has:
- Clear "Get Started" section at top
- Registration link prominent
- Benefits of registering (10x requests)

---

## Measurement

| Metric | Now | Target |
|--------|-----|--------|
| PyPI downloads → Satoshi API registrations | ~0% | 5% |
| RPC proxy anonymous → registered | unknown | 10% |
| bitcoin-mcp client_type in API logs | track | measure |
