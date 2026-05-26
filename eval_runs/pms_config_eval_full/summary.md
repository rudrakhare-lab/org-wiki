# PMS Config Evaluation Summary

Generated: 2026-05-07T20:35:24
Total evaluated rows: **1798**

## Outputs

- row jsonl: `eval_runs/pms_config_eval_full/pms_config_eval_rows.jsonl`
- row csv: `eval_runs/pms_config_eval_full/pms_config_eval_rows.csv`
- summary: `eval_runs/pms_config_eval_full/summary.md`
- .in workbook: `eval_runs/pms_config_eval_full/All WIS CONFIGS.evaluated.xlsx`
- .com workbook: `eval_runs/pms_config_eval_full/wis_service_configs (1).evaluated.xlsx`

## Server Counts

| Server | Rows |
|---|---:|
| `com` | 1119 |
| `in` | 679 |

## Flag Counts

| Flagged | Rows |
|---|---:|
| `NO` | 1481 |
| `YES` | 317 |

## Confidence Counts

| Confidence | Rows |
|---|---:|
| `HIGH` | 1475 |
| `LOW` | 91 |
| `MEDIUM` | 169 |
| `REVIEW` | 62 |
| `UNKNOWN` | 1 |

## Most Flagged Sheets

| Server:Sheet | Flagged Rows |
|---|---:|
| `com:7. Email Emp Experience` | 58 |
| `com:9. Emp Exp Common Config` | 48 |
| `in:9. Emp Exp Common Config` | 26 |
| `com:1. PMS` | 22 |
| `in:7. Email Emp Experience` | 21 |
| `com:6. Guard App` | 20 |
| `in:6. Guard App` | 19 |
| `com:2. VMS` | 17 |
| `com:3. Meeting Rooms` | 16 |
| `in:1. PMS` | 15 |
| `com:5. WIS Seat Booking` | 12 |
| `in:5. WIS Seat Booking` | 10 |
| `com:8. Emp Exp Internal Config` | 9 |
| `in:2. Visitor Mgmt` | 8 |
| `in:3. Meeting Rooms` | 8 |
| `in:8. Emp Exp Internal Config` | 4 |
| `com:4. Booking Rule Engine` | 4 |

## Top Flag Reasons

| Reason | Rows |
|---|---:|
| Only inventory/raw context found; no operational Jira or rich wiki evidence | 176 |
| No meaningful source description, rich wiki context, or exact Jira evidence | 81 |
| Coverage confidence is REVIEW | 60 |

## Rubric

A row is flagged when it has weak answer readiness: missing meaningful description, no rich wiki context, no exact Jira evidence, low confidence, or noisy/generic Jira matches.

Coverage dimensions are purpose, data type, behavior, scope, default/values, dependencies, Jira examples, and rich wiki context.
