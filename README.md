# fmap: Worli property guides and funnels

A free-tools setup for selling three ebooks and a shortlist service to three Worli customer segments.

## What is here

| Path | What it is |
|---|---|
| `data/properties.csv` | The 19-project register, from the Worli knowledge base (9 Oct 2026). Only verified prices are shown. |
| `scripts/validate_register.py` | Checks the register on every push. Fails if a price is marked verified without a range, or a shortlisted project has no RERA ID. |
| `docs/strategy/funnel.md` | The three layers: free checklist, paid ebook, shortlist handoff. |
| `docs/strategy/segments.md` | End user, investor, legacy buyer. Each is labelled as a hypothesis until real replies arrive. |
| `docs/strategy/compliance.md` | RERA agent rules, DPDP data rules, accuracy rules. Read before going live. |
| `products/ebooks/` | Outlines for three ebooks, one per segment. |
| `data/leads/README.md` | Schema for the Google Sheet. Lead data does not go in this repo. |
| `site/index.html` | Landing page for GitHub Pages with a lead-capture button. |
| `.github/workflows/` | `validate.yml` checks the register. `pages.yml` deploys the site. |

## Free stack

- **Hosting:** GitHub Pages (`site/`)
- **Checks and automation:** GitHub Actions (free for public repos; check the minutes limit for private ones)
- **Lead capture and storage:** Google Forms and Google Sheets
- **Email:** Gmail, sent by hand for the first 100 leads, then a free-tier mailing list
- **Payments for ebooks:** a free-to-list store such as Gumroad (charges a fee per sale)

## Before going live

1. Replace `FORM_ID` in `site/index.html` with the real Google Form.
2. Add the agent registration number to the footer of `site/index.html`.
3. Confirm the ebook prices with 20 readers, then set them in `products/ebooks/`.
4. Work the open items in `data/properties.csv`. The MahaRERA complaint counts and the OC checks need a person at the portal.
5. Have a lawyer or a RERA-registered agent review `docs/strategy/compliance.md`.

## Limits

- The knowledge base is a dated snapshot. Re-verify the register each quarter.
- The segments are hypotheses until real replies come in from Layer 1.
- This repo does not send email or take payments. Those steps are done in the tools above.
