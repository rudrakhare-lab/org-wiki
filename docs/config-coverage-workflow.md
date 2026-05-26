# Config Coverage Workflow

This workflow checks whether important product config keys are actually covered
in the current LLM wiki strongly enough for support and product teams to use.

## Why this matters

For WorkInSync, many operational questions are really config questions:

- What does this property do?
- Which module owns it?
- What happens if it is enabled or disabled?
- Is it BUID-level, office-level, or global?
- What other workflows depend on it?

If the key exists only in raw docs, or appears once with no explanation, the
wiki is not yet reliable for config-heavy usage.

## Input format

Prepare a CSV or TSV with at least:

| Property Name | Description |
|---|---|
| `exampleConfigKey` | Short explanation of what this config controls. |

Suggested location:

`raw/configs/config_inventory.csv`

## Run the audit

From the repo root:

```bash
python3 scripts/audit_config_coverage.py \
  --input raw/configs/config_inventory.csv \
  --report docs/config-coverage-report.md \
  --csv docs/config-coverage-report.csv
```

## What the audit checks

For each config key, the script looks for exact key mentions across:

- `wiki/`
- `raw/`
- `docs/`
- `config/`

## Status meanings

- `covered`
  - the config is present in wiki pages strongly enough to be usable
- `thin`
  - the config exists in wiki, but context is too shallow
- `raw-only`
  - the config exists in source/raw material, but has not been promoted into wiki knowledge
- `missing`
  - the exact config key is not found anywhere scanned

## How to use the results

### 1. `missing`

These are the highest-priority gaps.

Action:
- search Jira for the config name
- search additional raw docs / release notes / config sheets
- if still absent, flag as unknown coverage gap

### 2. `raw-only`

These configs are present in source material but not in module knowledge yet.

Action:
- update the relevant module page
- add a dedicated `Key Configurations` section if needed
- mention enable/disable behavior and scope

### 3. `thin`

These configs are visible, but not documented deeply enough.

Action:
- add richer notes:
  - module ownership
  - scope (`BUID`, office, org, user)
  - default behavior
  - dependent workflows
  - known risks / caveats

## Recommended follow-up enhancement

Once the first audit is done, create a first-class wiki page type for configs,
for example:

- `wiki/configs/<config-key>.md`

That would let the agent answer config questions more directly and consistently.
