# Referral Program — bitcoin-mcp

*Created: 2026-03-17*

---

## Assessment

**Premature.** A referral program needs:
1. Users who love the product (need to validate with first Pro customers)
2. Something to refer TO (need self-serve Stripe checkout first)
3. Volume to make it worthwhile (256 downloads/mo is too low)

---

## When to Revisit

Trigger: 50+ Satoshi API registrations from bitcoin-mcp users AND 5+ Pro subscribers.

## Proposed Structure (for when ready)

**"Install & Refer" Program:**
- Existing user shares unique referral link
- New user installs bitcoin-mcp + registers for Satoshi API key via referral link
- Both get: 1 month of Pro free (or $5 credit toward Pro)
- Referral tracked via UTM + referral code in registration

**Implementation:**
- Add `referral_code` column to `api_keys` table
- Generate unique codes for registered users
- Track referral source on registration
- Automated credit via Stripe coupon

**Cost:** $19/referral (1 month Pro for each party). Break-even if referred user stays 2+ months.

---

## What to Do NOW Instead

The best "referral program" at this stage is:
1. Make bitcoin-mcp so good people naturally tell others (product-led growth)
2. Ask happy users: "Know anyone building with Bitcoin + AI?" (manual referral)
3. Cross-promote in MCP communities (organic word-of-mouth)

Don't build infrastructure for a program nobody will use yet.
