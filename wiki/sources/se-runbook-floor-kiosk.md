---
type: source
ingested: 2026-06-29
doc_type: misc
sources_bundle: true
---

# Source Summary — SE Runbook: Floor Kiosk Topic

> This page summarises the floor-kiosk–related source documents distilled from
> `/tmp/fk_inputs.md` (Phase D of the SE runbook ingest series). Documents are from
> the team's "Conwo WorkInSync Docs" Google Drive, SE / implementation engineering authorship.

## Source Documents Covered

| Doc Title | Raw File | Date | Notes |
|-----------|----------|------|-------|
| WorkInSync Floor Kiosk Specification Sheet v1.0 | `raw/se-runbook/crawl/files/1JiKa1u42kbRJyms6__aFusHxhX9DGFlnDyQ1ZY_qZ-0.docx` | 2026-02-02 | Device hardware spec — primary spec sheet |
| Device Specification Datasheet — Android-based Floor Kiosk | `raw/se-runbook/crawl/files/1_zYUYUOE_l9tDU2_VIL20Hwr2-nLsflw20cy8lxRSqU.docx` | undated | More detailed datasheet with CPU arch, GPU requirements, unsupported hardware list |
| Employee Flow Setup — Master Property: `isEmployeeFlowEnabled` | `raw/se-runbook/crawl/files/1N-IfBxVJU_ETdYQSPBZCA1tUngLV_zv1KFGJjmt-A8A.docx` | undated | Config setup doc for the employee self-checkin kiosk flow |
| Setting Up Scalefusion on Android and iPad Devices | `raw/se-runbook/crawl/files/1V2f7ByWFnZAxqI4dwlslVdJsGotwXUmAiVLAfUryCjY.docx` | undated | MDM enrollment procedure (generic; examples use MR Kiosk naming) |
| Custom Forms on Self Checkin Flow (i.e. tablet flow) | `raw/se-runbook/crawl/files/1eJ1vJCyxDXMQ1XR3KDitpCT7SJ_Gq4QCDh8r131kttM.docx` | undated | Consul JSON schema for `visitorFormsMetaData` custom form fields |

**Skipped (noise / cross-linked to correct module):**

| Doc | Reason |
|-----|--------|
| Meeting Room Kiosk Setup v1.1 | Meeting-rooms content — cross-linked to [[modules/meeting-rooms]] |
| Meeting room kiosk Scalefusion | Meeting-rooms MDM variant — cross-linked to [[modules/meeting-rooms]] |
| Visitor Management PRD | Visitor-management topic → [[modules/visitor-management]] |
| VMS KT Sprint 10/11/12 | Visitor-management topic (check-in notifications, digipass, front-desk config) → [[modules/visitor-management]] |
| Discovery questions to ask | Visitor-specific discovery (`visitor*`, `emailListTo*`, `formsMetaData*` props) → [[modules/visitor-management]] |
| Parking Management PRD | Parking topic → [[modules/parking-management]] (already ingested) |
| WorkInSync Parking Setup | Parking topic → [[modules/parking-management]] |
| Parking Technical Document | Parking topic → [[modules/parking-management]] |
| Seat Allocation and Utilization dashboard | Desk/seat management topic → [[modules/desk-management]] |
| WorkInSync Meeting Rooms Setup | Meeting-rooms SE setup → [[modules/meeting-rooms]] |
| TABS: MoveInSync Mobile / WorkInSync Mobile | Mobile app topic → [[modules/mobile-app]] |

---

## Key Takeaways

- **Two hardware spec documents exist** (Spec Sheet v1.0 + Device Datasheet) with minor divergences on GPU minimum (Adreno 619 vs 640) and working frequency (~2.1–3.7 GHz vs up to 2.4 GHz). Both are preserved in the module with explicit conflict callouts.
- **Unsupported GPU/CPU list** is documented only in the Datasheet: Mali-400/450/T720/T760, Rockchip RK30xx, older MediaTek MT65xx/MT67xx are disqualified. OpenGL ES 3.2 + Vulkan 1.1 + hardware-accelerated WebView are mandatory GPU requirements.
- **Scalefusion MDM** manages device enrollment, kiosk lock mode, app pushes, and remote monitoring. Two enrollment methods: `afw#mobilock` (preferred for new Android) and APK install (fallback). iPad enrollment uses a Configuration profile downloaded via Safari.
- **`isEmployeeFlowEnabled`** is a sub-key inside `visitorKioskConfigs` (VISITOR service), not a standalone PMS row. Enabling it requires also setting `employeeDescriptionHeaderText` (multilingual) and `DefaultEndTimeOfEmployeeBooking = 1439`.
- **Self-checkin custom forms** are controlled by `visitorFormsMetaData` (Consul JSON, VISITOR service). Fields are typed (`input`/`singleselect`), validated (`Required`, `MinLength`, `Email`), and scoped by visitor type via `parentConfigValue` (e.g. `businessGuest`, `contractor`, `delivery`, `employee`).
- **RemoteCast** (Scalefusion's remote monitoring app) must be installed and permissions granted on each device during enrollment — it is not auto-configured.
- **Device naming** in the source doc uses meeting-room naming (`<OrgName> - <Room> MR Kiosk`) as its only example — floor-kiosk naming convention is not explicitly documented.
- **No secrets found** in the floor-kiosk source documents — enrollment QR codes and group codes appear as blanks/placeholders in the source. Zero `eyJ…` tokens.

---

## Modules Mentioned

- [[modules/floor-kiosk]] — primary module (device hardware, MDM, employee flow, self-checkin)
- [[modules/meeting-rooms]] — cross-linked for MR kiosk Scalefusion content (not duplicated)
- [[modules/visitor-management]] — owns `visitorKioskConfigs`, `visitorFormsMetaData`, and the VISITOR service where `isEmployeeFlowEnabled` lives

---

## Entities Mentioned

- `kiosk-device` — Android/iPad hardware device enrolled in Scalefusion MDM
- `visitorFormsMetaData` — Consul JSON array defining self-checkin form fields (owned by VISITOR service)
- `visitorKioskConfigs` — Consul JSON blob containing kiosk configuration including `isEmployeeFlowEnabled`

---

## Decisions Extracted

None extracted — documents are operational SOPs and hardware specifications, not architecture decisions.

---

## Config Properties Documented

| Property | Location / Service | What the doc says | Default |
|----------|--------------------|-------------------|---------|
| `isEmployeeFlowEnabled` | Sub-key of `visitorKioskConfigs` in VISITOR service | Enables employee flow on the visitor/self-checkin kiosk; set to `true` to activate | Not documented (source says "set = true"; no explicit default stated) |
| `employeeDescriptionHeaderText` | Sub-key of `visitorKioskConfigs` in VISITOR service | Multilingual header shown to employees on the kiosk screen (en/es/fr/nl) | Not documented |
| `DefaultEndTimeOfEmployeeBooking` | VISITOR service | Controls end time of employee booking made via kiosk; value `1439` = 23:59 end of day | Not documented |
| `visitorFormsMetaData` | Consul JSON, VISITOR service | Array of form field definitions for self-checkin tablet flow; see [[modules/floor-kiosk]] §Self-Checkin for field schema | Not documented |

> ⚠️ `isEmployeeFlowEnabled`, `employeeDescriptionHeaderText`, and `DefaultEndTimeOfEmployeeBooking`
> are VISITOR-service properties surfaced here because the source doc (Employee Flow Setup) is
> filed under the floor-kiosk source bundle. Their authoritative config page is
> [[configs/visitor-management]]. The visitor-management config page is auto-generated (total 157
> configs, generated 2026-06-09) — these properties may need to be added manually and protected
> from regen overwrites if not already present.

---

## Secrets Redacted

**Zero secrets found.** Scanned all five source documents:
- No `eyJ…` JWT tokens
- No `Bearer` tokens
- No Scalefusion API keys
- Enrollment codes and QR codes appear as blanks or placeholder descriptions (not actual values)

Total redactions: **0**

---

## Wiki Pages Created / Updated

- **Created:** [[runbooks/floor-kiosk-device-setup]] — new runbook covering Android and iPad enrollment into Scalefusion MDM
- **Created:** [[sources/se-runbook-floor-kiosk]] (this page)
- **Updated:** [[modules/floor-kiosk]] — enriched with:
  - Expanded Hardware Specifications table (dual-source comparison with conflict callouts)
  - Unsupported Hardware section (GPU/CPU blacklist from Device Datasheet)
  - Scalefusion MDM section (enrollment overview + cross-link to runbook)
  - Employee Flow Kiosk section (`isEmployeeFlowEnabled`, `employeeDescriptionHeaderText`, `DefaultEndTimeOfEmployeeBooking`, custom fields)
  - Self-Checkin Tablet Flow & Custom Forms section (`visitorFormsMetaData` schema)
  - Updated frontmatter: `last_updated` → 2026-06-29; appended `[[sources/se-runbook-floor-kiosk]]` to source list

---

## Open Questions

- GPU minimum discrepancy: Spec Sheet (2026-02-02) lists Adreno 619; Device Datasheet lists Adreno 640 as minimum. Which is current? Confirm with hardware team.
- Working frequency discrepancy: "~2.1–3.7 GHz (Ryzen 5 baseline)" vs "up to 2.4 GHz" — two different framings of the same spec. Confirm with hardware team.
- Floor kiosk device naming convention: source only shows `<OrgName> - <Room> MR Kiosk` (meeting-room example). What is the floor-kiosk naming pattern?
- `isEmployeeFlowEnabled` auto-gen risk: the `visitor-management.md` config page is auto-generated. If `isEmployeeFlowEnabled` is not in the generated data, it needs manual addition with protection from regen overwrites.
- Scalefusion QR code and group enrollment code provisioning: who generates these and where are they stored? Not documented in any source.
- RemoteCast sleep-mode known issue (devices not picking up app updates after being left asleep): no confirmed fix documented — escalate to Scalefusion support.
