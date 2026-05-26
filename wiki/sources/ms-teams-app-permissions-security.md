---
type: source
raw_path: raw/modules/ms-teams-integration/WiS - MS Teams App - Permissions & Security (Client Shareable).docx
ingested: 2026-05-26
doc_type: spec
---

# WiS — Microsoft Teams App — Permissions, Security & Installation

## Source Title
WorkInSync - Microsoft Teams Integration: Permissions, Security & Installation (Client Shareable)

## Date
08/01/2024 (v1.2 approved 08-Jan-2024). Version history: v1.0 approved 15-Mar-2021 ("First version"); v1.1 approved 01-Apr-2022 ("Permissions update"). Author across all versions: Aditya Dutta. Approvers: Nitin Awasthi (v1.0/v1.1), Ujjwal Trivedi (v1.2). Document Control table classifies the document as **Internal** (despite the "Client Shareable" suffix in the filename — apparent inconsistency in source metadata).

## Type
spec

## Key Takeaways
- The WorkInSync MS Teams app is **Publisher Attested** under **Microsoft 365 App Compliance** — quote: *"the WorkInSync App on Microsoft Teams is Publisher Attested and adheres to the Microsoft 365 App Compliance"*.
- **No Microsoft customer data** is processed or stored — quote: *"The WorkInSync App and any underlying infrastructure does not process any data relating to a Microsoft customer or their device"* + *"does not store any Microsoft customer data"*.
- Identity is via **Microsoft Identity Platform (Azure AD)** — quote: *"WorkInSync integrates with Microsoft Identity Platform (Azure AD) for single-sign on, API access"*. The app *"adheres ... to the best practices outlined in the Microsoft identity platform integration checklist"* (source has a minor typo "adheres and to"; corrected here).
- Permissions are presented in **two perspectives** in the source: the user-facing **consent-prompt language** in the top-level `Permissions` section (6 scopes named in plain English), and the **technical use-case mapping** in the `Leveraging Microsoft Graph APIs` sub-section (named scopes + WorkInSync use cases). Deduped across both views: **11 distinct Graph scopes** — 10 Delegated + 1 Application (`MailBoxSettings.Read`, used only to fetch mailbox timezone for region identification).
- **MFA scope is internal infrastructure only** — source explicitly names three areas: **Code Repositories**, **DNS Management**, **Credential/Key Stores**. The source does NOT claim end-user MFA — user authentication goes through Azure AD SSO, a separate layer.
- **GDPR-compliant with three named capabilities**: delete personal data on request; restrict / limit processing; correct / update personal data.
- **Commercial: three plans on two marketplaces.** Plans: **Free** (up to 50 users), **Standard**, **Professional**. Available on the **Microsoft Teams Marketplace** (primary) and **Microsoft AppSource** (alternative); transactable with one-time payment + Microsoft-issued invoice. License management split: **WorkInSync portal** handles individual assignment (People → Employees: invite, assign, deactivate, reactivate); **Microsoft Admin Center** handles license purchase only — quote: *"Individual assignments cannot be done here"*.
- **Three installation pathways**: (a) per-user self-install with `Consent as an Employee` prompt at first use; (b) admin-managed org-wide install with one-time `Consent as an Admin` granted by an Azure AD admin; (c) auto-install via Microsoft Teams **app setup policies**. Two built-in policies named in source: **Global (Org-wide default)** and **FirstlineWorker** (for Frontline Workers; not customizable). Custom policies are supported. The source documents a 6-step admin procedure for creating a custom setup policy (Teams admin center → Teams apps > Setup policies → Add → name → Add apps → search "WorkInSync" → Add).

## Entities Mentioned
(none — operational / compliance document; no WorkInSync data entities introduced)

## Modules Mentioned
- [[modules/ms-teams-integration]] (primary subject)
- [[modules/sso]] (Azure AD identity is the auth backend referenced in the Identity sub-section)
- [[modules/meeting-rooms]] (downstream consumer per pre-existing wiki link — not directly named in this source)

## Decisions Extracted
(none — descriptive doc; no architectural decisions with alternatives + rationale recorded)

## Wiki Pages Created/Updated
- Created: [[modules/ms-teams-integration]]
- Updated: [[index]], [[log]]

_Source: [[sources/ms-teams-app-permissions-security]]_
