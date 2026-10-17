# Lead records

Lead data does not go in this repo. This folder holds only the schema, so the team knows what the Google Sheet should contain.

Create the Google Form and link it to a Google Sheet owned by the business. Use these columns, in this order:

| Column | Source | Notes |
|---|---|---|
| timestamp | Form | Set by Google Forms |
| name | Form, required | |
| email | Form, required | |
| segment | Form, required | `end_user`, `investor`, or `legacy` |
| layer | Sheet (manual) | `1_free`, `2_paid`, or `3_shortlist` |
| consent_text | Form | The exact wording shown to the lead |
| consent_given | Form, required | Checkbox, must be ticked |
| source_page | Form (hidden field) | Which page the lead came from |
| phone | Layer 3 only | Ask at handoff, not at sign-up |
| budget_cr | Layer 3 only | Optional |
| timeline | Layer 3 only | Optional |
| status | Sheet (manual) | `new`, `contacted`, `shortlisted`, `closed`, `unsubscribed` |
| notes | Sheet (manual) | No sensitive personal data |

## Retention and access

- Share the sheet only with the people who work the leads.
- Delete a row on request. Keep the unsubscribe list so the person is not re-added.
- Review the sheet every quarter and remove rows that have been unsubscribed for more than 12 months.
