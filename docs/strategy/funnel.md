# Three-layer funnel

Every layer uses only free tools: GitHub Pages for the site, Google Forms and Sheets for leads, GitHub Actions for checks, and Google Drive for the files.

| Layer | Who it is for | What they get | What we collect | Next step |
|---|---|---|---|---|
| 1. Free | Anyone researching Worli | Free checklist: "Before you visit a Worli project" | Name, email, segment, consent | Email sequence (3 emails, manual send from Gmail at first) |
| 2. Paid guide | Buyers and investors who want depth | One of three ebooks (see `products/ebooks/`) | Purchase via a payment page (Gumroad or similar) | Offer to book a shortlist call |
| 3. Done-with-you | Qualified buyers with a budget and timeline | A shortlist from `data/properties.csv` and a verification pass on MahaRERA | Budget, timeline, purpose, consent to share with a licensed agent | Handoff to a licensed agent (see compliance) |

## Rules for every layer

- Only show a price when `price_verified` is `yes` in `data/properties.csv`. Otherwise show "price on request".
- Every claim links to the RERA ID. Nothing says "guaranteed return" or "best investment".
- Each email and page carries the disclaimer in `docs/strategy/compliance.md`.
- A lead moves up a layer only after they ask for it.

## Measures to track (in the lead sheet)

- Layer 1 sign-up rate from site visits
- Layer 1 → Layer 2 conversion within 30 days
- Number of Layer 3 requests and how many become shortlists
- Unsubscribe rate on each email (keep it under 2%)
