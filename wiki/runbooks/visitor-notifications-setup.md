---
type: runbook
module: visitor-management
team: SE
status: active
last_updated: 2026-06-29
source: "[[sources/se-runbook-visitor-management]]"
raw_path: raw/se-runbook/crawl/files/1jLLg-rKq-7rKXoE1r6S9vQ-ux3_mM-fS9e1-fZvDJ4M.docx
---

# Visitor Notifications Setup — Property-Controlled Notification Config

## Purpose
Enable and configure property-controlled VMS notifications, including the notification panel UI and per-persona notification routing (host, creator, additional recipients).

## Prerequisites
- VMS enabled for the BUID.
- Understanding of which visitor-event notifications the client wants to control (invite sent, check-in, check-out, approval, cancellation, etc.).
- Confirm whether the client needs the full property-controlled mode or only default email/SMS notifications.

## Ordered Steps

### Step 1 — Opt the BUID into property-controlled notifications

Property-controlled notifications are **opt-in per BUID**. The master gate is:

```
PMS property:  enabledBuidForVisitorConfigs
Type:          LIST
Value:         Add the target BUID to this list
Server:        both (.in and .com)
```

Once a BUID appears in `enabledBuidForVisitorConfigs`, the three per-persona properties below become active for that BUID. Without this opt-in, the backend ignores those properties.

### Step 2 — Configure per-persona notification routing

Three backend properties control which notifications go to which persona:

| Property | Controls | Type | Server |
|----------|----------|------|--------|
| `hostNotifications` | Notifications sent to the **host** (employee who created the invite) | JSON | both |
| `creatorNotifications` | Notifications sent to the **creator** (if different from host) | JSON | both |
| `externalNotifications` | Notifications sent to **additional recipients** | JSON | .com only |

Set each property as a JSON object defining which notification events are enabled for that persona. The exact event keys match the event IDs defined in `notificationMetaData` (Step 3).

> ⚠️ `externalNotifications` is `.com` server only. For `.in` clients, additional-recipient notifications cannot be property-controlled via this path.

### Step 3 — Configure the notification panel UI

Two properties together govern the notification panel that appears in the VMS UI:

**`notificationMetaData`** (JSON, both servers) — defines the panel structure:
- Each notification entry has a **group** (section heading) and a **question** (notification type label).
- Each question has **options** that determine which checkboxes appear on the UI (e.g. "Host", "Creator", "Additional Recipients").
- Groups are configurable: can be renamed; notifications can be moved between groups.

**`notificationConfigs`** (JSON, both servers) — defines the **default state** of each checkbox:
- Maps notification IDs to their default checked/unchecked state.
- The property name `notificationConfigs` is also referred to as "Property Name" in the source doc.

> ⚠️ **Consistency rules (must be enforced):**
> 1. The **grouping** must be identical between `notificationMetaData` and `notificationConfigs`.
> 2. The **ID** of each notification entry must be identical between `notificationMetaData` and `notificationConfigs`.
>
> Mismatched grouping or IDs cause the notification panel to render incorrectly or silently drop entries.

### Step 4 — Add the notification privilege

For the notification panel to be accessible to the appropriate roles, add:

```
Privilege: PrivilegeConfigurations_Visitor_Management_Notifications
```

Add this privilege to each role (e.g. RECEPTIONIST, ADMIN) that should be able to view and modify notification settings from the UI.

### Step 5 — Validate

1. Log in as a user with the notification privilege.
2. Open Visitor Management → Notification Settings.
3. Verify all notification groups and checkboxes match the configured `notificationMetaData`.
4. Verify default states match `notificationConfigs`.
5. Create a test invite and check-in a test visitor — confirm notifications reach the host, creator, and (if `.com`) additional recipients as configured.

## Screenshots
Source document (`1jLLg-rKq-7rKXoE1r6S9vQ-ux3_mM-fS9e1-fZvDJ4M.docx`) is the primary reference. No UI screenshots were captured in the SE crawl text extract.

## Validation
- `enabledBuidForVisitorConfigs` contains the target BUID.
- Notification panel renders with correct groups and checkboxes.
- A test check-in event triggers notifications to all configured personas.
- No "duplicate notification" or "missing notification" reports from the client after go-live.

## Notes & Gotchas
- `externalNotifications` (additional recipients) is `.com` only. For `.in` clients, this persona is not property-controllable — document this explicitly in the client's setup notes.
- Grouping and ID consistency between `notificationMetaData` and `notificationConfigs` is the most common misconfiguration — validate both JSONs against each other before deployment.
- The privilege `PrivilegeConfigurations_Visitor_Management_Notifications` is not in the auto-generated PMS config table; it is a Stratus/privilege-service entry, not a PMS property.
- MS Teams notification templates (`approveMsTeamsTemplate`, `visitorCheckinMsTeamsTemplate`, etc.) are separate properties — they control Teams message content, not the notification panel. See [[modules/ms-teams-integration]].

## Related Jira
—

## Linked Raw Evidence
- `raw/se-runbook/crawl/files/1jLLg-rKq-7rKXoE1r6S9vQ-ux3_mM-fS9e1-fZvDJ4M.docx` — "VMS Notifications on UI + Property-Controlled Notification"

_Source: [[sources/se-runbook-visitor-management]]_
