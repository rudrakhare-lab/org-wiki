# PMS Runtime API Playbook

This playbook structures the PMS dashboard APIs captured from DevTools/Postman.
It is for read/debug workflows first. Do not document real bearer tokens,
cookies, employee ids, or customer-sensitive config dumps in repo files.

## Goal

When a user asks why a feature is behaving incorrectly, the assistant should not
stop at the 1,800 static config definitions. It should identify the exact runtime
config value for the requested customer context:

```text
service + propertyName + BUID + optional OFFICEID + optional ROOMID/ROLE
```

The answer should say:

- what the config means, using wiki/Jira/default-property evidence
- which customization criteria are supported for that property
- what value is configured at each relevant level
- which level appears to be causing the behavior
- which exact BUID/office/room/role config the user should change

## Service Criteria Matrix

The coarse service-level matrix is in `config/pms_service_scope_matrix.toml`.
Always refine it with the property-level `criteriaPriorityList` from
`default-properties/details`.

| Service | Known Criteria |
|---|---|
| `PROJECT-MANAGEMENT-SERVICE` | `BUID`; special `ROLE` criteria for role-specific properties |
| `MEETING_ROOMS` | `BUID`, `OFFICEID`, `ROOMID` |
| `VISITOR` | `BUID`, `OFFICEID` |
| `EMP_EXP_INTERNAL_CONFIGURATIONS` | `BUID` |
| `BOOKING-RULE-ENGINE` | `BUID`, `OFFICEID` |
| `EMAIL_EMPLOYEE_EXPERIENCE` | `BUID` |
| `WIS-SEAT-BOOKING` | `BUID`, `OFFICEID` |
| `GUARD_APP` | `BUID`, `OFFICEID` |
| `EMPLOYEE_EXPERIENCE_COMMON_CONFIG` | `BUID` |
| `APP_SERVER_CONFIG` | `BUID` |
| `ETS` | `BUID`, `OFFICEID` |

For `PROJECT-MANAGEMENT-SERVICE`, observed `ROLE` values include:

```text
cd210644-153b-4a57-aa48-5e7213a5da66
employee
RECEPTIONIST
```

Keep these as observed values, not a complete enum, until confirmed by the PMS
team.

## Auth Setup

Use environment variables locally:

```bash
export PMS_TOKEN='paste bearer token without Bearer prefix'
export PMS_COOKIE='paste dashboard cookie string if required'
```

Never commit `PMS_TOKEN`, `PMS_COOKIE`, `JSESSIONID`, `mis_sso`,
`sso-wis-token-*`, employee GUIDs, or customer-specific dumps.

## Endpoint Catalog

### 1. Default Property Metadata

Purpose: list all configurable properties for a service, with type, default/base
value, definition, and `criteriaPriorityList`.

```http
GET /propmanagement/api/{SERVICE_ID}/default-properties/details
Header: ServiceId: {SERVICE_ID}
```

CLI:

```bash
venv/bin/python scripts/pms_api_client.py default-properties \
  --service VISITOR \
  --out raw/pms-api/VISITOR.default-properties.json
```

Use this to answer:

```text
Does property X exist?
What type is it?
Can it be customized at BUID/OFFICEID/ROOMID/ROLE?
What is the PMS-owned definition?
```

### 2. Service Access and BUIDs

Purpose: get the current user's access role for a service and the BUIDs visible
to that user.

```http
GET /propmanagement/api/user/service/{SERVICE_ID}/roles
Header: ServiceId: {SERVICE_ID}
```

CLI:

```bash
venv/bin/python scripts/pms_api_client.py roles \
  --service VISITOR \
  --out raw/pms-api/VISITOR.roles.json
```

Use this to validate whether the BUID the user asks about is visible to the
current credentials.

### 3. Criteria Value List

Purpose: list allowed raw values for a criterion such as `OFFICEID`.

```http
GET /propmanagement/api/{SERVICE_ID}/criteria-value-list/{CRITERIA}
Header: ServiceId: {SERVICE_ID}
```

CLI:

```bash
venv/bin/python scripts/pms_api_client.py criteria-values \
  --service VISITOR \
  --criteria OFFICEID \
  --out raw/pms-api/VISITOR.OFFICEID.values.json
```

Observed output for `OFFICEID` is a list of IDs. This is not enough to map office
names to IDs. We still need the office-directory API that returns office name
and office id for a BUID.

For Meeting Rooms, expect a similar flow for `ROOMID`, but capture and verify it
from DevTools before building resolver logic.

### 4. Current Runtime Properties

Purpose: fetch current property values for a service at a specific criteria
context.

```http
POST /propmanagement/api/{SERVICE_ID}/properties/v2
Header: ServiceId: {SERVICE_ID}
Body: criteria object
```

BUID-level:

```json
{"BUID": "genpactindia-GInd"}
```

Office-level:

```json
{"BUID": "genpactindia-GInd", "OFFICEID": "000-0000-0000-000000096334"}
```

Expected room-level shape for Meeting Rooms, to verify:

```json
{"BUID": "example-BU", "OFFICEID": "example-office-id", "ROOMID": "example-room-id"}
```

Expected role-level shape for Project Management Service, to verify:

```json
{"BUID": "example-BU", "ROLE": "employee"}
```

CLI:

```bash
venv/bin/python scripts/pms_api_client.py properties \
  --service VISITOR \
  --buid genpactindia-GInd \
  --out raw/pms-api/VISITOR.genpactindia-GInd.properties.json
```

```bash
venv/bin/python scripts/pms_api_client.py properties \
  --service VISITOR \
  --buid genpactindia-GInd \
  --criteria OFFICEID \
  --value 000-0000-0000-000000096334 \
  --out raw/pms-api/VISITOR.genpactindia-GInd.office.properties.json
```

The response is a list:

```json
[
  {
    "propertyName": "kioskInviteOptions",
    "propertyValue": ["CHECKIN_EMAIL", "CHECKOUT_EMAIL"],
    "propertyDefinition": "Controls QR-based check-in and check-out options on kiosk."
  }
]
```

This endpoint gives the runtime value set for the exact criteria body you pass.

## Query Workflow

For every user query about a config:

1. Identify likely `service_id` and `propertyName` from the 1,800 config catalog.
2. Read `default-properties/details` for that service/property.
3. Check `criteriaPriorityList` for allowed criteria.
4. If more context is needed, ask the user for the missing level:
   - BUID
   - office name or `OFFICEID`
   - room name or `ROOMID` for Meeting Rooms
   - role for Project Management Service role-scoped properties
5. Convert human names to IDs:
   - office name -> `OFFICEID` using the office-directory API, still missing
   - room name -> `ROOMID` using the room-directory API, still missing
   - role label -> `ROLE` value, confirmed from DevTools per property
6. Fetch BUID-level values using `properties/v2`.
7. Fetch lower-level values using `properties/v2` with `OFFICEID`, `ROOMID`, or
   `ROLE`.
8. Compare the returned values and explain whether the lower-level value differs
   from the parent BUID value.
9. Combine with wiki/Jira evidence to explain what the config does and what
   exact level should be changed.

## Missing APIs To Capture

The current prompt gives enough to fetch raw runtime values by criteria, but the
resolver still needs:

- office directory API: BUID -> office name + `OFFICEID`
- room directory API: BUID + office -> room name + `ROOMID`
- update/save API: request body for changing a property value
- audit/history API if available: who changed a property and when

Capture these in DevTools by performing the matching UI action, then copying the
request as cURL and replacing secrets with placeholders.

## Important Interpretation Rules

- `default-properties/details` gives metadata and default/base values.
- `properties/v2` gives current runtime values for the criteria body.
- `criteriaPriorityList` is property-specific. Do not rely only on service-level
  scope.
- Do not guess whether priority `1` or the larger number wins. Preserve the raw
  list until engineering confirms PMS lookup precedence.
- Missing lower-level response is not the same as explicit `false` or empty list.
- If a user asks about office/room behavior but only gives BUID, ask for the
  office/room before recommending a change.

