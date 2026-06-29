---
type: runbook
module: meeting-rooms
team: SE
status: active
last_updated: 2026-06-29
source: "[[sources/se-runbook-meeting-rooms]]"
raw_path: raw/se-runbook/crawl/files/1z5F39r8hNTWzmsK_OCHAo5K4yBB2nzskUTvcdqffX0o.docx
---

# Runbook — Outlook Room Calendar Integration

## Purpose & Scope

Pre-implementation discovery checklist and SE setup guide for integrating WIS Meeting Rooms
with Outlook/Exchange calendar (bidirectional sync and Outlook Add-in).

Covers:
1. Outlook version requirements and integration mode selection
2. Pre-implementation discovery questionnaire (identity, privacy, booking policy, timezone, access control, sync edge cases, Add-in)
3. WIS-side configuration keys for Outlook integration

> ⚠️ **Staleness caveat — 2021 source.** This document is dated 2021. The curated module page
> (`[[modules/meeting-rooms]]`) covers the current Outlook integration model (CONSENT_TYPE,
> wis-integration service, Add-in manifest URL) and should be treated as the authoritative
> reference. Treat specific host names, endpoint paths, and permission scopes in this runbook as
> **"Previously documented (2021)"** — verify against current implementation before using in a
> client-facing context. Flag any discrepancies to the PM.

_Source: [[sources/se-runbook-meeting-rooms]] (Outlook Pre-Impl Discovery, 2021)_

---

## Prerequisites

- BUID provisioned and office premise created
- Meeting Rooms enabled (`MEETING_ROOM_ENABLED` = `true`) — see [[runbooks/meeting-room-setup]]
- Client has an active Microsoft 365 (O365) tenant
- Admin access to client's Exchange/M365 Admin Center (for verifying room mailbox configuration)
- WIS Bearer token for `wis-integration`/`outlook` service endpoints
- `CONSENT_TYPE` decision made (ADMIN vs USER level) — see Step 3

---

## 1. Outlook Version Requirements

| Version | Bidirectional Sync | Add-in | Catering |
|---|---|---|---|
| O365 (Microsoft 365) | ✅ | ✅ | ✅ |
| Outlook 2019, 2021 | ✅ | ✅ (limited) | ✅ |
| Outlook < 2019 | ✅ | ✗ Not supported | — |
| Integrated + native setup | O365 only | — | — |

> ⚠️ Microsoft has announced end-of-support for O-2019 and O-2021. All clients should be on O365. The bidirectional sync works on any version as long as correct Graph API permissions are granted.

---

## 2. Integration Mode

Two integration modes are available:

| Mode | Description | Config |
|---|---|---|
| **Admin consent** | WIS is granted permissions via the client's M365 admin for all users/rooms | `CONSENT_TYPE` = `ADMIN` (default) |
| **User consent** | Each user individually grants WIS access to their calendar | `CONSENT_TYPE` = `USER` |

> ⚠️ Admin consent is the standard and recommended path. User consent requires each employee to
> complete an OAuth flow and is operationally difficult to maintain at scale.
>
> **Previously (2021)**: the document describes both paths as equally common. **Current recommendation
> (per [[modules/meeting-rooms]])**: `CONSENT_TYPE` defaults to `ADMIN`; confirm with PM before
> choosing USER mode.

---

## 3. Pre-Implementation Discovery Questionnaire

Before configuring the integration, collect answers from the client's Exchange/IT admin.
Each item maps to a potential WIS configuration or code behaviour.

### A. Email & Identity

| Question | Exchange Config to Check | WIS Impact |
|---|---|---|
| Do users book using alias/secondary email? | Mailbox proxy addresses | WIS must map aliases to `primarySmtpAddress` — code handles this, but verify |
| Do room resources have multiple email aliases? | Room mailbox proxy addresses | Room matching logic needs all aliases; flag if rooms return as unavailable |
| Do users book via service accounts? | App registration / service account permissions | WIS sees service account as organizer; on-behalf-of handling may be needed |
| Will external/federated users book rooms? | `Set-CalendarProcessing -ProcessExternalMeetingMessages $true` on room | WIS user-creation logic for unknown users; flag to dev |

### B. Privacy & Sensitivity

| Question | Exchange Config | WIS Impact |
|---|---|---|
| Do users mark meetings 'Private'? | `RemovePrivateProperty` on room mailbox | WIS loses meeting title without organizer name; handled in code |
| Is Microsoft Purview sensitivity labelling used? | Purview label config | Encrypted meeting bodies may not be readable by WIS; error message needed |
| Should meeting subjects appear on room calendars? | `DeleteSubject` (default `$true` = removes subject) | If `$true`, WIS gets blank/organizer-only subject — verify with client preference |
| Does organizer name prefix the subject? | `AddOrganizerToSubject` (default `$true`) | WIS receives "John Smith: Team Meeting"; parsing may be needed |

### C. Booking Policies & Approval

| Question | Exchange Config | WIS Impact |
|---|---|---|
| Are rooms configured to auto-accept? | `AutomateProcessing=AutoAccept` | Standard flow; WIS treats accepted = confirmed |
| Do any rooms require delegate approval? | `AllBookInPolicy=$false`, `ForwardRequestsToDelegates=$true` | WIS must track Tentative until delegate approves; confirm with client |
| Is there a minimum meeting duration? | `MinimumDurationInMinutes` (default 0) | Add-in must validate short bookings before submitting |
| Are double-bookings allowed? | `AllowConflicts=$false` (default) | Standard; WIS rejects conflicting submissions |

### D. Timezone & Regional

| Question | Exchange Config | WIS Impact |
|---|---|---|
| What timezone are room mailboxes in? | `Get-MailboxCalendarConfiguration` → `WorkingHoursTimeZone` | WIS must use correct timezone for Graph API calls |
| Do users book from different timezones? | Use `Prefer: outlook.timezone` header on Graph API | Mismatch causes wrong-time bookings — verify handling |
| Are there rooms in multiple geographic regions? | Each room has its own timezone | WIS must track per-room timezone; not a single-BUID-timezone assumption |
| Are there all-day bookings? | `isAllDay=true`, times at midnight | WIS must handle the all-day flag |

### E. Access Control & Room Restrictions

| Question | Exchange Config | WIS Impact |
|---|---|---|
| Can all users book all rooms? | `AllBookInPolicy=$true` vs `$false` | If `$false`, WIS must enforce the policy client-side; flag to dev |
| Are some rooms restricted to specific groups? | `BookInPolicy` with allowed users/groups | WIS room availability must reflect restrictions |
| Are rooms organized into room lists? | Room lists = Exchange distribution groups | WIS Add-in room finder should use room lists for filtering |

### F. Sync Edge Cases

| Question | Exchange Config | WIS Impact |
|---|---|---|
| Do rooms show Tentative status until approved? | `TentativePendingApproval=$true` | WIS sync must distinguish Tentative vs Accepted — verify |
| Can external users cancel their bookings? | External cancellation processing | WIS cancel sync may fail for external users; manual cleanup may be needed |
| Is auto-release for no-shows enabled on Exchange? | `EnableAutoRelease` + `PostReservationMaxClaimTimeInMinutes` | WIS receives cancellation when Exchange auto-releases; note that WIS also has its own `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` — both may fire |
| Is room capacity enforced? | `EnforceCapacity=$true` | Exchange rejects WIS bookings over capacity; Add-in should pre-validate |

### G. Outlook Add-in Considerations

| Question | Impact |
|---|---|
| Which Outlook clients are used (Desktop/Web/Mobile)? | Add-in support varies; test all platforms used by client |
| Is "New Outlook for Windows" used? | New Outlook has different add-in behaviour from Classic Outlook; verify compatibility |
| Do users book via mobile Outlook? | Mobile add-in support is limited; set user expectations |

---

## 4. WIS-Side Configuration

Set these BUID-level properties after completing the discovery questionnaire:

| Property | Default | Notes |
|---|---|---|
| `CONSENT_TYPE` | `ADMIN` | `ADMIN` or `USER` — see Step 2 above |
| `ENABLE_WITH_PRINCIPAL_NAME` | `true` | Outlook integration uses the UPN (principal name) for matching |
| `BUILDING_PREMISE_NAME` | — | On Stratus sites, controls the entity name shown in Outlook |
| `CREATE_PREMISE_IF_IT_DOESNT_EXIST` | — | Allows system creation of the premise if it doesn't exist in Exchange |
| `ENABLE_AUTO_MEETING_ROOM_SYNC` | — | Automatically runs the room sync job |
| `DEACTIVATION_TYPE` | — | Controls behaviour when a meeting room is deactivated |

> ⚠️ **Previously (2021)**: the pre-impl doc references consent-URL endpoints under
> `wis-integration.workinsync.io/outlook/...`. Per [[modules/meeting-rooms]] Dependencies,
> the Outlook/Google sync runs via the `wis-integration`/`outlook` service — **this is distinct
> from the `ms-teams-integration` module**. Confirm current endpoint base URLs with the
> implementation team before sending consent URLs to the client.

---

## 5. Validation

- [ ] Admin consent flow completed: client M365 admin has granted WIS the required Graph API permissions
- [ ] `CONSENT_TYPE` set correctly (ADMIN or USER)
- [ ] Test room created in WIS with calendar type = `OUTLOOK`, room mailbox email address set
- [ ] Bidirectional sync test: create a booking in WIS → confirm it appears in the room's Outlook calendar
- [ ] Bidirectional sync test: create a booking in Outlook → confirm it appears in WIS
- [ ] Add-in deployed: manifest URL distributed to test user; Add-in appears in Outlook
- [ ] Add-in test: book a room via the WIS panel inside Outlook; confirm booking appears in WIS admin
- [ ] Cancel test: cancel from WIS → room freed in Outlook; cancel from Outlook → room freed in WIS

---

## Screenshots / Evidence

Raw source: `raw/se-runbook/crawl/files/1z5F39r8hNTWzmsK_OCHAo5K4yBB2nzskUTvcdqffX0o.docx`

---

## Notes & Gotchas

- **2021 source — verify before client engagement.** The discovery questionnaire format is still useful but specific Exchange cmdlets, permission scopes, and endpoint URLs should be confirmed against current Microsoft documentation and the WIS implementation team's runbook.
- **Two auto-release mechanisms can coexist.** Exchange `EnableAutoRelease` and WIS `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` are independent. If both are active for a room, they may each trigger separately. Coordinate with the client on which should be the primary mechanism.
- **Dynamic Policy does NOT apply to Outlook rooms.** Tag-based access control (Dynamic Policy) affects only WIS-native rooms. If the client is using Outlook rooms, enforce room restrictions via Exchange `BookInPolicy` instead.
- **New Outlook for Windows compatibility.** New Outlook (2024+) has different add-in manifest requirements. If the client is rolling out New Outlook, verify the Add-in manifest version with the product team.
- **`BUILDING_PREMISE_NAME`** is only relevant for Stratus-hosted sites. Confirm with implementation whether the client is on Stratus before setting.

---

## Related Jira

—

---

## Linked Raw Evidence

- [[sources/se-runbook-meeting-rooms]] — Outlook Pre-Impl Discovery doc (2021)
- [[sources/outlook-integration-permissions]] — PRD: Outlook consent/permissions model
- [[sources/outlook-addin-setup]] — PRD: Add-in manifest deployment guide
