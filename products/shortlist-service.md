# Shortlist service (Layer 3)

## What the buyer gets

- Projects that fit their segment and budget, from `data/properties.csv`, produced by `orchestrator.py match`.
- For each project: the MahaRERA ID, status, price range with its date, and everything still unverified.
- A handoff to a MahaRERA-registered agent for site visits and the purchase.

## Process

1. The buyer submits the shortlist form (budget, timeline, purpose, consent to share with an agent).
2. We run `python3 toolkit/orchestrator/orchestrator.py match --segment <segment> --budget-cr <budget>`.
3. A person re-checks every matched project on MahaRERA the same day and updates the register if anything changed.
4. We send the shortlist with the disclaimer, and introduce the agent only with the buyer's consent.
5. The agent handles visits, negotiation and the sale. We never take deposits.

## Fees

How we are paid (a research fee from the buyer, or a referral arrangement with the agent) must be decided with a lawyer before launch, and stated to the buyer in writing. Do not charge until that is settled.
