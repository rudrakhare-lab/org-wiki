---
type: runbook
module: employee-provisioning
last_updated: 2024-08-31
sources:
  - "[[sources/se-runbook-employee-provisioning]]"
related:
  - "[[runbooks/ets-data-sync]]"
  - "[[modules/sso]]"
  - "[[modules/ms-teams-integration]]"
---

# Runbook — Employee Data Sync via SCIM (SE Setup Guide)

## Purpose & Scope

This runbook covers the **SE-side setup and troubleshooting** for syncing employee records
into WorkInSync via **SCIM 2.0** from Azure AD (Entra ID) or Okta.

**This runbook is for SCIM/IdP provisioning only.** It does NOT cover:
- ETS-side SFTP or API data sync (transport/commute clients) → see [[runbooks/ets-data-sync]]
- Stratus Direct API mode (WorkInSync-only sites, batch REST) → see [[modules/employee-provisioning]] §API Endpoints
- SSO (authentication) → see [[modules/sso]]. SCIM provisioning and SSO are separate: SCIM uses a WIS-issued secret token; SSO uses IdP OAuth/SAML. They are often set up together (especially for Azure AD / Okta customers) but are independent functions.
- MS Teams integration → see [[modules/ms-teams-integration]]. Azure AD is often the IdP for both SCIM and Teams; the Azure AD app for SCIM is a separate enterprise application from the Teams integration.

_Source: [[sources/se-runbook-employee-provisioning]]_

---

## When to Use This Runbook

- Client wants to auto-provision employees from Azure AD (Entra ID) or Okta into WorkInSync
- Client reports provisioning failures, users not appearing, or deprovisioning not working
- Setting up SCIM for a new WorkInSync tenant (Stratus site)

---

## Prerequisites (Collect Before Starting)

- [ ] Hosting region confirmed: **AWS Singapore** (`scim.workinsync.io/scim/v2`) or **EU** (`scim.eu.workinsync.io/scim/v2/`)
- [ ] SCIM secret token generated — reach out to **KDV / EI-Auth Team** to obtain the token for this client. The token is unique per client and issued by the WIS account manager.
- [ ] Client's IdP type: **Azure AD (Entra ID)** or **Okta**
- [ ] Client has admin access to their Azure Portal / Okta portal
- [ ] For Azure AD: Azure admin credentials for `portal.azure.com`
- [ ] For Okta: Okta developer/admin access at `developer.okta.com`

> ⚠️ **Never share the wrong regional URL.** A Singapore URL shared with an EU client (or vice-versa) causes "Test Connection" to fail. Confirm region before sharing credentials.

---

## Part A — Azure AD (Entra ID) Setup

### Step 1 — Create the Enterprise Application

1. Log in to `https://portal.azure.com` with administrator credentials.
2. Navigate to **Enterprise Applications** (from frequently-used apps or global search).
3. Click **New Application** → **Create your own application**.
4. Give it a memorable name (e.g. `MoveInSync/WorkInSync SCIM`).
5. Select **"Integrate any other application you don't find in the gallery (Non-gallery)"** and click **Create**.

### Step 2 — Configure Provisioning

1. In the application, open **Provisioning** → **Get Started**.
2. Set **Provisioning mode** to **Automatic**.
3. In **Admin Credentials**:
   - **Tenant URL**: `https://scim.workinsync.io/scim/v2` (Singapore) or `https://scim.eu.workinsync.io/scim/v2/` (EU)
   - **Secret Token**: the token from KDV/EI-Auth (share this with the client securely; redact to `<token>` in all tickets)
4. Click **Test Connection**. A success message enables the Mappings section below.

### Step 3 — Configure Mappings

1. Expand **Mappings**.
2. **Disable** "Provision Azure Active Directory Groups" — WorkInSync does NOT support group sync.
3. **Enable** "Provision Azure Active Directory Users".
4. Click into Users mapping and review:
   - **Source object scope**: default is active accounts. Can apply filters (e.g. only users from one office).
   - **Target object actions**: leave Create, Update, Delete all enabled.
5. **Attribute mappings** — confirm the following are present (Azure maps these by default; remove or ignore extras):

| Azure AD attribute | SCIM attribute | WorkInSync use |
|---|---|---|
| `userPrincipalName` | `userName` | Primary unique ID |
| `displayName` | `displayName` | Name |
| `mail` | `emails[type eq "work"].value` | Email |
| `givenName` | `name.givenName` | First name |
| `surname` | `name.familyName` | Last name |
| `physicalDeliveryOfficeName` | `addresses[type eq "work"].formatted` | Office |
| `mailNickname` | `externalId` | Required by SCIM protocol |
| `employeeId` | `...enterprise:2.0:User:employeeNumber` | Optional (preferred for commute clients) |
| `department` | `...enterprise:2.0:User:department` | Team |
| `manager` | `...enterprise:2.0:User:manager` | Reporting manager |
| `Switch([IsSoftDeleted],,…)` | `active` | Deprovisioning flag — **must be mapped** (see Troubleshooting §T-3) |

> ⚠️ Address and phone attributes (`streetAddress`, `city`, `state`, `postalCode`, `country`, `telephoneNumber`) are **commute clients only**. Skip for workplace-only deployments.

6. Save attribute mappings.

### Step 4 — Start Provisioning

1. Go back to the Provisioning overview.
2. Set **Provisioning Status** to **On**.
3. Initial sync runs automatically. Subsequent syncs run on Azure's default ~40-minute cycle.
4. Monitor via **Provisioning logs** in the portal — each user shows Create/Update/Delete status and any error codes.

---

## Part B — Okta Setup

### Step 1 — Add the SCIM Application

1. Log in to `https://developer.okta.com/login/`.
2. Go to **Applications → Applications → Browse App Catalog**.
3. Search for **SCIM 2.0**. Select **SCIM 2.0 Test App (Header Auth)** (the Header Auth variant matches WorkInSync's token mechanism).
4. Click **Add Integration**. Set the application name on the General Settings page.

### Step 2 — Configure API Integration

1. Go to the **Provisioning** tab → **Configure API Integration** → **Enable API Integration**.
2. **Base URL**: `https://scim.workinsync.io/scim/v2` (Singapore) or `https://scim.eu.workinsync.io/scim/v2/` (EU)
3. **API Token**: the token from KDV (redact to `<token>` in all tickets)
4. Click **Test API Credentials** — must succeed before saving.

### Step 3 — Configure Provisioning Actions

1. Under **Provisioning → To App**, enable:
   - Create Users
   - Update User Attributes
   - Deactivate Users
2. Review **Attribute Mappings**. Okta attribute → SCIM attribute mapping follows the same table as Azure AD above.

### Step 4 — Assign Users / Groups

Assign the Okta application to the relevant users or groups. Provisioning runs when users are assigned; deprovisioning runs when they are unassigned or deactivated.

---

## Part C — Mandatory Fields by Site Type

| Field | Stratus (WorkInSync-only) | ETS/transport site |
|---|---|---|
| Email | **Mandatory** | Mandatory |
| Employee ID | Optional (preferred for commute) | **Mandatory** |
| Office | Optional (defaults to default office/team if absent) | Mandatory |
| Team | Optional | Mandatory |

If office and team are not provided for a Stratus site, the employee is provisioned to the **default office and team** configured for the BUID.

---

## Part D — Deprovisioning (User Removal)

SCIM sends an `active: false` boolean when a user is removed in the IdP. WorkInSync's SCIM server interprets this as a deactivation/remove.

> ⚠️ **The `active` attribute MUST be mapped in the IdP.** If this mapping is missing or misconfigured, deprovisioning silently fails — users remain active in WorkInSync even after removal in the IdP. This is the most common deprovisioning failure.

**Azure AD fix:**
- Go to SCIM App → Overview → Manage → Provisioning → **Provision Azure Active Directory Users**
- Find or add the mapping for `active`:
  - Target attribute: `active`
  - Source expression: `Switch([IsSoftDeleted], , "False", "True", "True", "False")`
- Save.

---

## Troubleshooting

### T-1 — "Test Connection" Fails

**Symptom:** Azure or Okta shows a connection failure when testing the SCIM credentials.

**Checklist:**
- [ ] Confirm the **regional URL** matches the client's hosting environment (Singapore vs EU). Wrong region = guaranteed failure.
- [ ] Confirm the **token** is the one generated for this specific client (tokens are client-specific).
- [ ] Token has not expired or been revoked. If in doubt, request a fresh token from KDV/EI-Auth.
- [ ] Network: if the client's IdP runs in a restricted network, the SCIM endpoint must be reachable (no egress firewall blocking `scim.workinsync.io`).

### T-2 — Provisioning Failures (User-level)

**Symptom:** Some or all users fail to provision; provisioning logs show errors.

**What to collect from the client:**
- Provisioning logs (Azure: the detailed per-user logs with WiS-side and Azure-side error codes)
- Email IDs of affected employees

**Common causes:**
1. **Mandatory attribute missing** — confirm the mandatory attributes are populated for affected users. For Stratus: Email. For ETS: Employee ID.
2. **Special characters** — unsupported characters in names or email may fail internal WiS validation. Check affected records for non-ASCII characters.
3. **SCIM server ↔ PII service cache mismatch** — an internal WiS issue. Escalate to: SCIM server team (Deepanshu / Tushar Tyagi), PII service team (Yogesh). Request a cache clear.
4. **Invalid office / team** — provisioning records that reference an office or team not yet configured in WorkInSync will fail. Verify that office names exist in the BUID before provisioning.

### T-3 — Users Not Being Removed (Deprovisioning Fails)

**Symptom:** Employees deactivated or removed in the IdP remain active in WorkInSync.

**Cause:** The `active` attribute mapping is missing or incorrect in the IdP SCIM app.

**Fix for Azure AD:** See Part D above — add or correct the `active` → `Switch([IsSoftDeleted],…)` mapping.

**Fix for Okta:** Under Provisioning → To App → confirm "Deactivate Users" is enabled. Check the `active` attribute mapping points to the Okta user's `status` field.

### T-4 — Provisioning Quarantine (Azure AD)

**Symptom:** Azure AD enters "Quarantine" state and stops processing provisioning for affected records.

**Cause:** The same provisioning error repeats for the same records in a short span. Azure quarantines the records to prevent repeated failures.

**Resolution:**
1. Collect SCIM provisioning logs from the client.
2. Do an initial triage — common Azure-side error codes may indicate a client-configuration issue (wrong attribute value, invalid office name, etc.).
3. If the root cause is not immediately clear, share the logs with a WiS developer for deeper analysis.
4. After fixing the root cause, the quarantine resolves on the next provisioning cycle, or can be triggered manually via "Provision on Demand".

### T-5 — User Provisioned to Wrong Office / Team

**Symptom:** Users appear in WorkInSync but assigned to the default office/team instead of their actual office.

**Cause:** The `physicalDeliveryOfficeName` attribute (office) is not mapped or is empty in the IdP for affected users.

**Fix:** Ensure the office attribute is populated in Azure AD / Okta and mapped to `addresses[type eq "work"].formatted` in the SCIM app.

---

## Related Pages

- [[modules/employee-provisioning]] — full module reference: all three sync modes, Stratus API fields, role/privilege model
- [[runbooks/ets-data-sync]] — ETS-side SFTP/API data sync (TechOps request process; separate from SCIM)
- [[modules/sso]] — IdP authentication (SSO). Often set up alongside SCIM but is a separate configuration.
- [[modules/ms-teams-integration]] — Teams integration also uses Azure AD; separate Azure enterprise app from the SCIM app.

## Last Updated
2024-08-31 — _Source: [[sources/se-runbook-employee-provisioning]]_
(Troubleshooting guide dated 2024-08-31; Azure/Okta setup guides dated 2021-09-15 / 2022-07-15)
