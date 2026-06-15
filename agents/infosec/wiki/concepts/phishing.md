---
type: concept
last_updated: 2026-06-15
---

# Phishing

Phishing is a social-engineering attack delivered by email (or SMS/voice — "smishing"/"vishing")
that tricks a user into revealing credentials, approving a fraudulent request, or running malware.

## Common variants
- **Credential harvesting** — a spoofed login page captures username/password.
- **Business Email Compromise (BEC)** — impersonation of an executive/vendor to authorize payments.
- **Spear phishing** — a targeted message crafted with personal/organizational detail.

## Mitigations
- Enforce **MFA** so a stolen password alone is insufficient.
- Deploy **DMARC/SPF/DKIM** to reduce domain spoofing.
- Use **link rewriting / safe-link** scanning at the mail gateway.
- Run **user-reporting** workflows (a "report phish" button) and periodic awareness training.
