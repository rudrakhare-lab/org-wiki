# PMS Config Evaluation Summary

Generated: 2026-05-07T20:25:38
Total evaluated rows: **20**

## Outputs

- row jsonl: `eval_runs/pms_config_eval_com_sample2/pms_config_eval_rows.jsonl`
- row csv: `eval_runs/pms_config_eval_com_sample2/pms_config_eval_rows.csv`
- summary: `eval_runs/pms_config_eval_com_sample2/summary.md`
- .com workbook: `eval_runs/pms_config_eval_com_sample2/wis_service_configs (1).evaluated.xlsx`

## Server Counts

| Server | Rows |
|---|---:|
| `com` | 20 |

## Flag Counts

| Flagged | Rows |
|---|---:|
| `NO` | 16 |
| `YES` | 4 |

## Confidence Counts

| Confidence | Rows |
|---|---:|
| `HIGH` | 16 |
| `REVIEW` | 4 |

## Most Flagged Sheets

| Server:Sheet | Flagged Rows |
|---|---:|
| `com:1. PMS` | 4 |

## Top Flag Reasons

| Reason | Rows |
|---|---:|
| Coverage confidence is REVIEW | 4 |

## Rubric

A row is flagged when it has weak answer readiness: missing meaningful description, no rich wiki context, no exact Jira evidence, low confidence, or noisy/generic Jira matches.

Coverage dimensions are purpose, data type, behavior, scope, default/values, dependencies, Jira examples, and rich wiki context.
