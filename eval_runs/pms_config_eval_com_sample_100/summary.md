# PMS Config Evaluation Summary

Generated: 2026-05-07T20:26:58
Total evaluated rows: **100**

## Outputs

- row jsonl: `eval_runs/pms_config_eval_com_sample_100/pms_config_eval_rows.jsonl`
- row csv: `eval_runs/pms_config_eval_com_sample_100/pms_config_eval_rows.csv`
- summary: `eval_runs/pms_config_eval_com_sample_100/summary.md`
- .com workbook: `eval_runs/pms_config_eval_com_sample_100/wis_service_configs (1).evaluated.xlsx`

## Server Counts

| Server | Rows |
|---|---:|
| `com` | 100 |

## Flag Counts

| Flagged | Rows |
|---|---:|
| `NO` | 78 |
| `YES` | 22 |

## Confidence Counts

| Confidence | Rows |
|---|---:|
| `HIGH` | 77 |
| `LOW` | 2 |
| `MEDIUM` | 6 |
| `REVIEW` | 15 |

## Most Flagged Sheets

| Server:Sheet | Flagged Rows |
|---|---:|
| `com:1. PMS` | 22 |

## Top Flag Reasons

| Reason | Rows |
|---|---:|
| Coverage confidence is REVIEW | 15 |
| Only inventory/raw context found; no operational Jira or rich wiki evidence | 6 |
| No meaningful source description, rich wiki context, or exact Jira evidence | 1 |

## Rubric

A row is flagged when it has weak answer readiness: missing meaningful description, no rich wiki context, no exact Jira evidence, low confidence, or noisy/generic Jira matches.

Coverage dimensions are purpose, data type, behavior, scope, default/values, dependencies, Jira examples, and rich wiki context.
