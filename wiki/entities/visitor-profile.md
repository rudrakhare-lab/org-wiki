---
type: entity
owned_by: visitor-management
used_by: [visitor-management]
last_updated: 2026-04-28
source: "[[sources/vms-prd]]"
---

# VisitorProfile

## Description
The persistent profile record for a visitor in the WIS system. Created at first invite and reused
for subsequent visits. Profile data is stored with consent (employee opt-in at invite time) and
subject to GDPR data deletion after X configurable days.
Distinct from VisitorInvite — the Profile persists across visits; the Invite is per visit.

## Fields
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| id | UUID | Unique visitor profile ID | Yes |
| name | string | Full name | Yes |
| email | string | Email address | Conditionally |
| phone | string | Phone number with country code | Conditionally |
| company | string | Visitor's employer | No |
| designation | string | Visitor's role/title | No |
| profile_photo | binary | Profile photograph (used on digipass + badge) | No (configurable) |
| identity_proof_type | enum | Document type (Passport, Aadhar, PAN, Driver's License, etc.) | No (configurable) |
| identity_proof_image | binary | Photo of identity document | No (configurable) |
| nda_accepted | boolean | Whether NDA was signed | No |
| nda_accepted_at | timestamp | When NDA was signed | No |
| nda_valid_until | date | Date NDA validity expires (configurable N days) | No |
| created_at | timestamp | Profile creation timestamp | Yes |
| gdpr_delete_after | date | Date profile must be deleted (per org GDPR config) | No |

_Note: email OR phone is mandatory — at least one must be present for identity verification._

## Used By
- [[modules/visitor-management]] — creates, manages, and reuses profiles across visits

## Relationships to Other Entities
- [[entities/visitor-invite]] — a VisitorProfile is linked to many VisitorInvites over time

## Source of Truth
[[modules/visitor-management]] owns the VisitorProfile entity.

_Source: [[sources/vms-prd]]_
