---
type: runbook
module: ms-teams-integration
team: SE
status: active
last_updated: 2026-06-29
source: "[[sources/se-runbook-ms-teams]]"
raw_path: raw/se-runbook/crawl/files/1pbXxmjFFlL_c1rwchY8vAhcCNUEKwRbWjZxm69CzRFE.docx
---

# Runbook: MS Teams Integration Setup

SE-facing guide for onboarding a client onto the WorkInSync MS Teams app. Covers both
onboarding pathways (existing Stratus client vs. new Teams-discovered client), admin consent
vs. per-user consent installation, and license management in both the WorkInSync portal and
the Microsoft Admin Center.

> ⚠️ **Source is from 2022 (v1.1, 2022-06-20).** The Teams Marketplace listing, pricing
> tiers, consent UX, and onboarding landing-page flow may have changed. Verify current UX
> with the product team before walking a client through these steps.

---

## Purpose

Enable IT admins and SE engineers to onboard a client organization onto the WorkInSync
Microsoft Teams app, configure organization-wide consent, and manage per-user license
assignment through both the WorkInSync portal and the Microsoft Admin Center.

---

## Prerequisites

Before starting, confirm with the client:

- [ ] **Microsoft 365 license**: every employee who will use the WorkInSync Teams app must
  have a valid MS Teams license (e.g. Microsoft 365 Business Standard or equivalent). The
  client's IT Administrator manages this via the **Azure Portal → Users → Licenses**.
- [ ] **IT Administrator access**: the client must have an Azure AD administrator available
  to grant org-wide consent (if using admin-managed install). Without an admin, each user
  will be prompted individually.
- [ ] **Identify the onboarding pathway** (see Step 1 below) — existing Stratus client or
  new client via Teams.
- [ ] **Identify the install model** — per-user consent, admin-managed consent, or
  admin-pushed via Teams app setup policies.

---

## Ordered Steps

### Step 1 — Identify the onboarding pathway

**Pathway A — Existing Stratus client**

Use this path if the client already has a Stratus instance (e.g. a `@workinsync.io`
organization URL) and is an existing paying WorkInSync customer.

- The client does **not** need to re-onboard or re-pay.
- They install the **Free** version of the Teams app only.
- On login, they use their **existing Stratus credentials** — no new account is created.
- The Teams app is a direct port of the Stratus instance; all their existing features and
  data are visible in Teams.

**Pathway B — New client discovered via Teams**

Use this path if the client found WorkInSync through the Teams Marketplace or Microsoft
AppSource and does not have a pre-existing Stratus instance.

1. Direct the client to the **Microsoft Teams Marketplace** (search "WorkInSync" in Teams)
   or **Microsoft AppSource** (`appsource.microsoft.com`).
2. The client selects a plan:
   - **Free** — up to 50 users; can upgrade later
   - **Standard** — see WiS Pricing Page for feature gating
   - **Professional** — see WiS Pricing Page for feature gating
3. Complete the **one-time purchase** process: place an order for the desired plan and
   initial license count. Microsoft sends an invoice to the buyer on completion.
4. After purchase, the buyer is directed to a **WorkInSync onboarding landing page** where
   the organization is provisioned into the WorkInSync system.
5. Purchasing or removing licenses can be done later from the WorkInSync web portal or the
   Microsoft Admin Center (see License Management below).

---

### Step 2 — Install the Teams app

**Per-user installation (no IT admin action required upfront)**

1. Employee navigates to the **App directory** in Microsoft Teams.
2. Searches for "WorkInSync" and clicks **Add**.
3. On first use, the employee is shown a **Consent as an Employee** prompt listing all
   required permissions. They review and consent.
4. After consent, the employee can use the app. Each new user repeats this step.

> If the app is installed from the Teams web app or desktop client, it automatically
> appears in the user's Teams mobile client as well.

**Admin-managed installation (recommended for org-wide rollout)**

1. The IT administrator (Azure AD global admin) installs the Teams app from the App
   directory.
2. On install, the admin is shown the **Consent as an Admin** prompt.
3. The admin reviews the full permission list and clicks to grant org-wide consent.
4. Once granted, **all existing and new users** can use the WorkInSync Teams app directly —
   no per-user consent prompt is shown again.

**Auto-install via Microsoft Teams app setup policies (optional)**

Teams admins can pre-install and pin the WorkInSync app for users using setup policies:
- **Global (Org-wide default)** — applies to all users not covered by another policy
- **FirstlineWorker** — for Frontline Workers; not customizable
- **Custom policies** — create a policy, add WorkInSync, assign to specific user groups

This installs and pins the app when Teams launches and during meetings — no user action
required.

---

### Step 3 — License management

**Via WorkInSync web portal (for individual user management)**

1. Log into the client's WorkInSync admin portal.
2. Navigate to **People → Employees** in the side-nav.
3. The employee list shows all users who have been assigned a license and marked as
   registered.
4. To add users: invite new users and assign a license.
5. To remove users: deactivate the user (this releases the license for reassignment) or
   reactivate if restoring.

**Via Microsoft Admin Center (for org-level seat counts)**

1. Log into the Microsoft Admin Center (`admin.microsoft.com`).
2. Navigate to the WorkInSync subscription.
3. Add or remove license purchases for the organization.
4. Note: individual user assignment **cannot** be done here — use the WorkInSync portal for
   that.

---

## Screenshots

Screenshots of the consent prompts, app directory search, onboarding landing page, and
portal license management screens are included in the source document. See raw evidence:
`raw/se-runbook/crawl/files/1pbXxmjFFlL_c1rwchY8vAhcCNUEKwRbWjZxm69CzRFE.docx`.

---

## Validation

After setup, confirm:

- [ ] At least one user can find and add the WorkInSync app in Teams
- [ ] The user can log in (existing Stratus creds for Pathway A; new account for Pathway B)
- [ ] Employee features are accessible: desk booking, WFH check-in/out, Find Teammate
- [ ] Bot responds to a basic command (e.g. "Show my bookings")
- [ ] Admin-consent path: a second user can install without seeing a consent prompt
- [ ] License count in the WorkInSync portal matches expectations

---

## Notes & Gotchas

- ⚠️ **2022 source** — the marketplace purchase UX, consent-prompt wording, and onboarding
  landing-page flow may have changed. Confirm current behavior with the product team or by
  walking through a sandbox install before client use.
- ⚠️ **Free plan limit**: the Free plan supports up to 50 users. Exceeding this requires
  upgrading to Standard or Professional.
- **IT admin availability**: if the client has no Azure AD admin available during onboarding,
  each user will hit the per-user consent prompt. Coordinate admin availability before the
  rollout date.
- **Teams mobile auto-propagation**: installing from the Teams web or desktop client
  automatically propagates to the Teams mobile app. This is Microsoft Teams mobile (not the
  WorkInSync `mobile-app` module).
- **License vs. access**: removing a user in the WorkInSync portal (deactivation) releases
  the WorkInSync license, but does not affect the user's MS Teams license or Azure AD
  account — those are managed separately by the IT admin.
- **Permission model**: the app uses delegated Graph API permissions (read-only for profile,
  presence, people list) plus one application permission (`MailBoxSettings.Read` for timezone
  detection). Full permission list: see [[modules/ms-teams-integration]] API Endpoints table.

---

## Related Jira

—

---

## Linked Raw Evidence

- Control document (v1.1, 2022-06-20): `raw/se-runbook/crawl/files/1pbXxmjFFlL_c1rwchY8vAhcCNUEKwRbWjZxm69CzRFE.docx`
- CS/Sales universe index: `raw/se-runbook/crawl/files/1Y1sPEoN5JIu7LNWc1U3WJ2LnTp6ss9Iv1yRefd2eus0.docx`
- Module page: [[modules/ms-teams-integration]]
- Source summary: [[sources/se-runbook-ms-teams]]
