# PMS Config Evaluation Workflow

This workflow evaluates whether the LLM wiki has enough evidence to answer
internal user questions about each PMS config on the `.in` and `.com` servers.

The goal is not to check whether a config has a description. A one-line
description is treated only as a hint. The evaluator looks for operational
answer readiness:

- what the config does
- how/when it should be enabled
- type, default, scope, and valid values
- connected/dependent configs
- rich wiki context beyond generated inventory pages
- Jira/customer evidence and ticket references

## Inputs

- `.in` workbook: `All WIS CONFIGS.xlsx`
- `.com` workbook: `wis_service_configs (1).xlsx`
- wiki/docs/raw corpus in this repo
- Jira SQLite mirror: `raw/jira/tickets.sqlite`

Duplicate config names across `.in` and `.com` are evaluated as separate rows,
because server context can differ.

## Scope Discovery

PMS configs are not only service-level definitions. Runtime values can exist at
different customer hierarchy levels:

- `BU`: business-unit/BUID-level config
- `OFFICE`: office-level override under a BUID
- `ROOM`: room-level override under an office

The current service scope matrix is stored in
`config/pms_service_scope_matrix.toml`.

| Service | Supported Levels |
|---|---|
| `PROJECT-MANAGEMENT-SERVICE` | `BU` |
| `MEETING_ROOMS` | `BU`, `OFFICE`, `ROOM` |
| `VISITOR` | `BU`, `OFFICE` |
| `EMP_EXP_INTERNAL_CONFIGURATIONS` | `BU` |
| `BOOKING-RULE-ENGINE` | `BU`, `OFFICE` |
| `EMAIL_EMPLOYEE_EXPERIENCE` | `BU` |
| `WIS-SEAT-BOOKING` | `BU`, `OFFICE` |
| `GUARD_APP` | `BU`, `OFFICE` |
| `EMPLOYEE_EXPERIENCE_COMMON_CONFIG` | `BU` |
| `APP_SERVER_CONFIG` | `BU` |
| `ETS` | `BU`, `OFFICE` |

Runtime API usage is documented in
[`docs/pms-runtime-api-playbook.md`](pms-runtime-api-playbook.md).

The CMS API for default property metadata is:

```bash
curl 'https://cmsapp.moveinsync.com/propmanagement/api/<SERVICE_ID>/default-properties/details' \
  -H 'Authorization: Bearer <TOKEN>' \
  -H 'ServiceId: <SERVICE_ID>' \
  -H 'Content-Type: application/json'
```

Do not commit real `Authorization`, `Cookie`, `JSESSIONID`, `mis_sso`,
`sso-wis-token-*`, employee GUID, or customer BUID values. Use environment
variables or a local `.env` file for authenticated calls.

This endpoint tells us how properties inside a service are configurable: BUID
level, office level, or room level. It does not by itself answer the effective
current value for a specific customer. For that, we need runtime property values
for the requested BUID/office/room.

### Default Properties API Response

Each response row represents one property definition inside the service:

| Field | Meaning |
|---|---|
| `propertyName` | PMS config key |
| `propertyValue` | default/base value from the service definition, not necessarily the customer's current override |
| `propertyDataType` | value type such as `BOOLEAN`, `INTEGER`, `STRING`, `LIST`, or `JSON` |
| `customizable` | whether PMS allows this property to be customized |
| `criteriaPriorityList` | hierarchy criteria where this property can be configured, for example `BUID`, `OFFICEID`, or `ROOMID` |
| `cloneable` | whether the property can be cloned/copied by PMS tooling |
| `groupName` | optional UI/logical group |
| `propertyDefinition` | PMS-owned definition/description |

Important: scope is property-specific. A service may support `BU + OFFICE`, but
some properties inside that service can still be BUID-only.

Do not infer precedence from memory. Preserve the raw `criteriaPriorityList`
until engineering confirms whether priority `1` or the larger number wins when
multiple values exist. The effective-value resolver must use the confirmed PMS
lookup order, not a guessed order.

To normalize a saved response into CSV:

```bash
venv/bin/python scripts/parse_pms_default_properties.py \
  --service VISITOR \
  --input raw/pms-default-properties/VISITOR.json \
  --out docs/visitor-default-properties.csv
```

## Effective Value Resolver

For customer debugging, the final system should answer:

> For this service, property, BUID, office, and optional room, what is the
> effective value and exactly where is that value coming from?

Resolution should be explicit about inheritance:

```text
ROOM value, if configured, overrides OFFICE.
OFFICE value, if configured, overrides BU.
BU applies when no lower-level override exists.
missing is not the same as false.
```

Example:

| Level | Value |
|---|---|
| BU | `true` |
| OFFICE | `false` |
| ROOM | not configured |

Effective value: `false`

Reason: office-level value is explicitly configured and overrides the BU value.

The resolver output should include:

- service and supported levels
- all raw values found at BU/office/room levels
- effective value
- override source level
- whether the lower-level value is missing or explicitly set
- recommended change level
- evidence from wiki/Jira explaining what the property does

The implementation should fetch values from
`POST /propmanagement/api/<SERVICE_ID>/properties/v2` for each relevant
criteria body:

```json
{"BUID": "example-BU"}
```

```json
{"BUID": "example-BU", "OFFICEID": "example-office-id"}
```

```json
{"BUID": "example-BU", "OFFICEID": "example-office-id", "ROOMID": "example-room-id"}
```

```json
{"BUID": "example-BU", "ROLE": "employee"}
```

The `ROLE` form is a Project Management Service exception and should be verified
per property from DevTools/default metadata.

## Runtime Data Needed

The current evaluator uses definition sources: Excel, wiki, docs, raw files, and
Jira. To resolve live customer state, add a separate runtime ingestion layer with
rows like:

| Field | Meaning |
|---|---|
| `server` | `.in` or `.com` |
| `service_id` | PMS service id, for example `VISITOR` |
| `property_name` | config key |
| `buid` | business unit id |
| `office_id` | optional office id |
| `room_id` | optional room id |
| `scope_level` | `BU`, `OFFICE`, or `ROOM` |
| `value` | configured value |
| `is_configured` | true when explicitly set at that level |
| `updated_at` | last modified timestamp if available |
| `source` | API/export/table used |

Until this runtime layer exists, the system can say what a config means and where
it may be configured, but it cannot safely say which value is active for a
specific customer context.

## Command

From the repo root:

```bash
venv/bin/python scripts/eval_pms_config_coverage.py \
  --out-dir eval_runs/pms_config_eval_full
```

Useful smaller runs:

```bash
venv/bin/python scripts/eval_pms_config_coverage.py --server in --limit 25
venv/bin/python scripts/eval_pms_config_coverage.py --server com --limit 25
```

Optional Claude evidence judge:

```bash
venv/bin/python scripts/eval_pms_config_coverage.py \
  --ask-claude \
  --limit 10 \
  --out-dir eval_runs/pms_config_eval_claude_sample
```

The deterministic run is the default because it can evaluate all configs without
model cost. `--ask-claude` asks Claude to judge the retrieved evidence for each
row and adds Claude-specific columns.

## Output Files

The evaluator writes:

- evaluated `.in` workbook with added columns
- evaluated `.com` workbook with added columns
- row-level CSV for filtering
- row-level JSONL for later automation
- `summary.md` with counts by server, sheet, confidence, and flag reason

## Flag Logic

A config is flagged when the evidence is not strong enough for reliable answers,
for example:

- no meaningful source description
- unknown service scope or unsupported level
- runtime values are unavailable for effective-value resolution
- no rich wiki context beyond generated config inventory
- no exact Jira ticket evidence
- low/unknown confidence
- noisy generic property names such as `admin`, `employee`, or `Analytics`

Flagged rows mean the team should enrich the wiki with purpose, enablement,
scope, default/value rules, dependencies, and Jira examples.
