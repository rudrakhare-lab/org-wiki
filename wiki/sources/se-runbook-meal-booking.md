---
type: source
raw_path: raw/se-runbook/crawl/files/1BIdHGbsUrTp4hEKy8pL8u4DNPMTfWhQl5zd7cv2iWTE.docx
ingested: 2026-06-29
doc_type: misc
---

# Source Summary — SE Runbook: Meal Booking Setup

## Source Title
Meal Booking — SE Configuration Runbooks (4 documents)

## Date
Not explicitly dated in source documents. Ingested 2026-06-29.

## Type
Operational runbook / SE configuration guide

## Documents Ingested

| Canonical File | Description |
|----------------|-------------|
| `raw/se-runbook/crawl/files/1BIdHGbsUrTp4hEKy8pL8u4DNPMTfWhQl5zd7cv2iWTE.docx` | "Meal Booking Workflow Setup" — primary setup steps (premise creation, mapping, Consul) |
| `raw/se-runbook/crawl/files/1-vBpXc3eg0STypByMS22SkP_zVh625iHqVaq4xgJePs.docx` | "Master property to enable meal" — PMS config properties and defaults |
| `raw/se-runbook/crawl/files/1JVY9qshShtAiIBGWD9iDkzA73YQ2n-FBLl4-9sy-U.docx` | "Create Counter" — counter creation, bulk mapping upload, QR generation; contained real auth tokens (redacted in wiki output) |
| `raw/se-runbook/crawl/files/1yVLbX83WWvjWbCjqcrRq4drtQjbp1DITSbCewfUYJ4g.docx` | Release Notes: "Meal booking Options Timewise" |

## Key Takeaways

- **Cafeteria setup uses `premiseType: "8"`** in the mis-security-guard premise service. The `premiseId` returned by the creation call is the anchor for all subsequent steps (counter creation, QR generation).
- **Two-service architecture**: cafeteria/counter management lives in `mis-security-guard`; counter-meal mapping and QR generation live in `meal-booking-app` (separate host and auth).
- **Consul controls meal types**: meal type codes (100=Breakfast, 101=Lunch, etc.) and option codes (0=None, 1=Veg, etc.) are set per-BUID at `employee-exp → <buid> → meal`. The master switch `mealPlanningEnabled` is in the common node.
- **One meal per employee per day**: enforced by `allowedMealBookingPerEmployee` (default=1 per BRE config). WFO-integrated meal and standalone meal booking are mutually exclusive.
- **Key PMS config defaults documented in source**: `allowedMealBookingPerEmployee`=1, `enableMealBookingNudge`=false, `enableMealConfigureKiosk`=false, `enableSeparateMealOption`=false, `mealCancelCutoffInMinutes`=-1440, `mealFinalStage`=['delivered','DELIVERED'], `excludeMealOnlyBookingsFromActiveBookingCount`=false.
- **Four new config properties referenced** (not currently in KB): `mealBookingEnabled`, `mealCheckinOptions` (default: `[Scan Meal QR]`), `enableMealFallbackFlow` (default: false), `enableMealQrPrintButtonenableMealQrPrint` (likely a concatenation error for two separate properties; default: false each). Server assignment not stated.
- **Auth tokens in "Create Counter" doc were real JWTs** — fully redacted to `<token>` in all wiki output. The doc captured a beta host (`mis-security-beta1...`); production equivalent used in runbook.
- **`mealCutoffInMinutes` default not documented** — the "Master property to enable meal" doc lists it as an existing property with no explicit default value stated.

## Entities Mentioned

- [[entities/meal-booking]] — meal booking record
- [[entities/cafeteria]] — cafeteria premise (`premiseType: "8"`)

## Modules Mentioned

- [[modules/meal-management]] — primary module
- [[modules/floor-kiosk]] — kiosk tablet at cafeteria
- [[modules/access-management]] — RFID check-in infrastructure

## Decisions Extracted

None — operational runbook, no architectural decisions documented.

## Wiki Pages Created / Updated

- **Created:** [[runbooks/meal-booking]] — full setup runbook (Steps 1–7)
- **Updated:** [[modules/meal-management]] — added SE setup workflow, key config properties, Related Runbooks section
- **Updated:** [[configs/booking-rule-engine]] — filled defaults for 6 meal-related properties
- **Updated:** [[configs/emp-experience-common]] — filled default for `excludeMealOnlyBookingsFromActiveBookingCount`; noted `mealCutoffInMinutes` default not documented
