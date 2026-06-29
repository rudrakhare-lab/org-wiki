---
type: module
status: active
owner: unknown
depends_on: [sso]
used_by: [meeting-rooms, visitor-management]
last_updated: 2024-01-08
source: "[[sources/ms-teams-app-permissions-security]], [[sources/se-runbook-ms-teams]]"
---

# MS Teams Integration Module

## Overview
MS Teams Integration is the surface that exposes WorkInSync inside Microsoft Teams. The
WorkInSync app is published on the **Microsoft Teams Marketplace** (primary) and on
**Microsoft AppSource** (alternative procurement channel) as a transactable app with three
pricing tiers (Free, Standard, Professional). It is **Publisher Attested** under Microsoft
365 App Compliance, processes and stores **no Microsoft customer data**, and authenticates
users via the **Microsoft Identity Platform (Azure AD SSO)**. The app calls Microsoft Graph
in delegated mode for read-only access to user profile, presence, contacts, and basic
profiles of other org users; one application permission (`MailBoxSettings.Read`) is used
only to fetch user mailbox timezone for region identification.

## Purpose & Scope
Owns the Teams-native entry point: the marketplace listings, the Microsoft Graph permission
model, the security and privacy posture, and the three installation pathways (per-user,
admin-managed, auto-install via app setup policies).

Does **not** own: WorkInSync's product features themselves (booking, meal, parking, etc. —
each owning module surfaces its own UI through this entry point), the Outlook / Google
calendar connector (related but unresolved — see Open Questions and `meeting-rooms`),
the WorkInSync mobile app (owned by `mobile-app`; the "appears in your mobile app"
behaviour described in the source refers to **Microsoft's Teams mobile client**, not the
WIS mobile-app module), or identity itself (owned by `sso`).

## Key Features
- **Microsoft Teams Marketplace listing**: app discoverable inside Teams; transactable purchase with one-time payment; Microsoft issues invoice on completion
- **Microsoft AppSource listing**: alternative procurement channel for organizations that source via AppSource
- **Three pricing tiers**: **Free** (up to 50 users), **Standard**, **Professional**; feature offering mirrors the WiS Pricing Page
- **License management — WorkInSync portal**: under **People → Employees**, admins see licensed employees; new users can be invited and assigned a license; users can be deactivated or reactivated
- **License management — Microsoft Admin Center**: add or remove license purchases at the org level; individual assignment cannot be done here — must use the WorkInSync portal
- **Onboarding post-purchase**: once the one-time purchase completes, the buyer is directed to a landing page where the organization is onboarded into WorkInSync
- **Per-user installation**: employees install from the Teams app directory; on first use, each user is prompted to grant `Consent as an Employee`
- **Admin-managed installation**: an Azure AD admin grants one-time org-wide consent via the `Consent as an Admin` prompt; all current and future users use the app without per-user prompts
- **Auto-install via Microsoft Teams app setup policies**: Teams admins use **app setup policies** — built-in **Global (Org-wide default)** and **FirstlineWorker** (for Frontline Workers; not customizable), or **Custom** policies — to install and pin the WorkInSync app for users when Teams launches and during meetings
- **Microsoft Graph delegated permissions**: read-only access to user profile, presence (own + all org users), relevant people list, and basic profiles of other org users; refresh-token access via `offline_access` — full permission table below
- **Microsoft Graph application permission**: `MailBoxSettings.Read`, used only to fetch the user's mailbox timezone for region identification
- **Publisher Attested compliance**: adheres to Microsoft 365 App Compliance; **no Microsoft customer data is processed or stored**; GDPR compliant with named capabilities for personal-data **delete**, **restrict / limit processing**, and **correct / update**; OWASP Top 10 vulnerability classes documented as prevented via an established vulnerability identification + risk-ranking process
- **MFA on internal infrastructure** (not product-side): the source explicitly names three areas where WorkInSync supports MFA — **Code Repositories**, **DNS Management**, and **Credential/Key Stores**. End-user MFA goes through Azure AD SSO (see `sso` module).

## Onboarding Pathways
Two distinct pathways depending on how the client discovered WorkInSync (as documented in the 2022 Integration Control Doc — verify current onboarding flow before client use):

- **Existing Stratus client** — client already has a Stratus instance (e.g. `xyz@workinsync.io` placeholder) and is a paying customer. They install the **Free** version of the Teams app and log in with their existing Stratus credentials. No re-onboarding and no re-payment required. The Teams app is a **direct port of the Stratus instance** — what they see on the web is what they see in Teams.
- **New client discovered via Teams** — client found WorkInSync through the Teams Marketplace or Microsoft AppSource. The app is transactable; they select a plan (Free ≤50 users / Standard / Professional), complete a one-time purchase (Microsoft issues invoice), and are directed to an onboarding landing page where their organization is provisioned into WorkInSync.

_Source: [[sources/se-runbook-ms-teams]]_

## Features Exposed in Teams

> ⚠️ As documented in the 2022 Integration Control Doc — verify current feature set before relying on this list; the product may have expanded since 2022.

### Employee features
- Create a desk booking or modify an existing one
- Check in when Working from Home; check out at end of day
- Find where teammates are working from and view their real-time presence
- Broadcast your own work location (WFH / WFO + selected desk) to colleagues

### People Manager features
- Receive notifications when team members start or end their day
- Receive booking and booking-update notifications from direct reports
- Create bookings, view today's / upcoming bookings and meetings
- View team activity — see where the team is working from

### Bot Commands (conversational / natural-language)
The WorkInSync bot understands conversational commands and natural-language variations:

| Command intent | Example invocation | Notes |
|---|---|---|
| Book a seat | "Book a seat" or variations | Bot prompts for remaining details |
| Fetch bookings | "Show my upcoming bookings", "Show my bookings for tomorrow" | Next booking or by date |
| Modify or cancel | Via booking-card options after fetching | Uses booking card UI within chat |
| Check-in / check-out | "Check in" / "Check out" | For WFH; notifies colleagues |
| Find a teammate | "Find [colleague name]" | Shows where the colleague is working from today |

### Tabs
**Personal Tabs (user's own context):**
- **Bookings Tab** — browse past and future bookings via a calendar control; edit or cancel future bookings
- **Team Activity Tab** — view whereabouts of frequently-worked-with people; searchable across the organization

**Team Tabs (shared team context):**
- **Team Activity Tab** — install in a Teams "Team" channel for a quick view of a specific team's working locations

_Source: [[sources/se-runbook-ms-teams]]_

## Data Entities Used
(none — this module is operational and compliance-oriented; the source introduces no WorkInSync data entities)

## Dependencies on Other Modules
- [[modules/sso]] — authenticates Teams users via **Microsoft Identity Platform** (Azure AD); the app follows the Microsoft identity-platform integration checklist for SSO and API access

## Used By
- [[modules/meeting-rooms]] — `meeting-rooms` frontmatter declares `depends_on: ms-teams-integration`; the specific calendar / Outlook contract is not defined in this source — see Open Questions

## API Endpoints
This module does **not** expose WorkInSync HTTP endpoints. It **consumes** Microsoft Graph endpoints under the permission scopes below.

| Permission | Type | Use |
|---|---|---|
| `User.Read` | Delegated | View user's basic profile (name, picture, username) |
| `People.Read` | Delegated | Read user's relevant people list (local contacts, directory contacts, recent communications) |
| `Presence.Read` | Delegated | Read user's own presence (activity, availability, status note, OOO, timezone, location) |
| `Presence.Read.All` | Delegated | Read presence of all users in the directory (same fields) |
| `User.ReadBasic.All` | Delegated | Read basic profile of other org users (display name, first/last name, email, photo); populates the Team Activity tab |
| `offline_access` | Delegated | Maintain access via refresh tokens when user is not active |
| `openid` | Delegated (OpenID) | Sign in users with work accounts via SSO; maintain login status |
| `email` | Delegated (OpenID) | Check whether the Teams account exists in WorkInSync; create account if not |
| `profile` | Delegated (OpenID) | Read employee data: `empName`, `empId`, `tenantId`, `email`, profile picture |
| `users.ReadAll` | Delegated (OpenID) | Access manager's email for booking-notification routing |
| `MailBoxSettings.Read` | Application | Fetch user mailbox timezone for region identification |

_Note: the source presents Graph permissions from two perspectives — the user-facing consent-prompt language in the `Permissions` section (6 scopes), and a technical use-case mapping in the `Leveraging Microsoft Graph APIs` sub-section (additional scopes named). The table above is the deduped union: 11 distinct scopes (10 Delegated, 1 Application). `User.ReadBasic.All` is named once with one row — the source mentions it from both perspectives (general "Read all users' basic profiles" + the specific Team Activity tab use); the row combines both uses._

_Note: this table reflects permission **scopes** named in the source. The mapping of each scope to specific Microsoft Graph REST endpoint paths (e.g. `/me`, `/me/presence`, `/users/{id}/mailboxSettings`) is not documented in the source. Update when an engineering reference is ingested._

## Open Questions
- **Partially resolved**: The 2022 Integration Control Doc (v1.1, 2022-06-20) now documents the features exposed in the Teams app — desk booking, WFH check-in/out, presence/teammate-finder, people-manager notifications, bot commands (book/fetch/modify/cancel/find), and personal+team tabs (Bookings Tab, Team Activity Tab). See `## Features Exposed in Teams` above. ⚠️ **This source is from 2022 — verify the CURRENT feature set** before using with clients; the product has likely evolved.
- **Outlook ownership**: `meeting-rooms.md` flags this as open ("Is the Outlook/Google integration connector managed inside `ms-teams-integration` or is it a separate service?"). This source covers MS Teams app permissions only — does NOT resolve the question. Leave deferred to Tier 2.5 `meeting-rooms` re-ingest, which has the `outlook-*` source docs. ⚠️
- **mobile-app coupling**: the source notes that installing on Teams web/desktop auto-propagates to the **Teams mobile client** — that is Microsoft's Teams app, not the WorkInSync `mobile-app` module. Confirm with team whether any data or feature flows between this module and `mobile-app`.
- **License-tier feature gating**: what is paywalled at Free vs Standard vs Professional? Source defers to the WiS Pricing Page without listing specifics.
- **Module owner**: doc names **Aditya Dutta** as author across v1.0 (2021-03-15) → v1.2 (2024-01-08), with approvers Nitin Awasthi (v1.0/v1.1) and Ujjwal Trivedi (v1.2). Owning team not stated.

## Last Updated
2024-01-08 — _Source: [[sources/ms-teams-app-permissions-security]]_
