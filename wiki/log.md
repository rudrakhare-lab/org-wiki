# Activity Log
Append-only. Format: `## [YYYY-MM-DD HH:MM] <operation> | <title>`

---

## [2026-06-04 09:16] feedback-apply | wrong_config — feedback b59a3148952d

- Score `2` feedback applied as Feedback Notes block.
- Patched: [[configs/visitor-management]]
- Answer ID: `dce3843acf6b`
- Correction summary: The actual default is 30 minutes, not 60.

---

## [RESET 2026-04-27] Wiki reset for real ingest
- All test pages cleared. Ready to ingest real WorkInSync feature docs.
- Per-feature folders created under `raw/modules/` matching the Conwo WorkInSync Docs Drive structure.

---

## [INGEST 2026-04-28] INGEST | floor-kiosk, delegation, employee-experience, digital-wayfinding, meal-management, implementation

**Sources ingested (8 more):**
- `DIY Floor Planner Version Control PRD.docx` → [[sources/diy-floor-planner-prd]]
- `Floor Kiosk Device Specification Data Sheet.docx` → [[sources/floor-kiosk-device-spec]]
- `WorkInSync Floor plan - Add | Update - SOP.docx` → [[sources/floor-plan-sop]]
- `Delegation PRD.docx` → [[sources/delegation-prd]]
- `Digital Wayfinding Implementation SOP.docx` → [[sources/digital-wayfinding-sop]]
- `Meal Check-in via Access Card PRD.docx` → [[sources/meal-checkin-prd]]
- `SOP for Launching WorkInSync on Live ETS Server.docx` → [[sources/launch-ets-sop]]
- _(emp-exp delegation doc = duplicate of delegation PRD — not re-ingested)_

**New module pages:** floor-kiosk, delegation, digital-wayfinding, employee-experience, meal-management, implementation
**New entity:** meal-booking
**New cross-module:** meal-access-management
**New decisions:** delegation-stateless-session, standalone-meal-booking-constraint
**Updated:** index.md, log.md, overview.md, cross-module/overview.md, glossary.md

---

## [INGEST 2026-04-28] INGEST | parking-management — 3 source documents

**Sources ingested:**
1. `Copy of Copy of Parking PRD.docx` → [[sources/parking-prd]]
2. `MoveInSync Workplace - Dynamic Policy for Parking.docx` → [[sources/dynamic-policy-parking]]
3. `Copy of Parking Waitlist - Overview & Screenshots.docx` → [[sources/parking-waitlist]]

**Pages created:**
- `wiki/modules/parking-management.md` (new)
- `wiki/entities/parking-slot.md` (new)
- `wiki/entities/parking-booking.md` (new)
- `wiki/cross-module/parking-tags-desk-parking.md` (new)
- `wiki/decisions/2026-04-28-parking-slot-allocation-priority.md` (new)
- All 3 source pages in `wiki/sources/`

**Pages updated:** `wiki/index.md`, `wiki/log.md`, `wiki/overview.md`, `wiki/cross-module/overview.md`, `wiki/glossary.md`

**Also fixed:** `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` config note — 180 min is deployment default; 15 min is recommended setting.

**Open questions flagged:**
- Parking cut-off time property name left blank in PRD
- Waitlist: does it auto-assign slot or notify employee to manually book?
- New slot onboarding requires MoveInSync team email — not self-serve

---

## [INGEST 2026-04-27 17:45] INGEST | meeting-rooms — 8 source documents

**Sources ingested:**
1. `Meeting Rooms App PRD.docx` → [[sources/meeting-rooms-app-prd]]
2. `Copy of Kiosk - Meeting Rooms PRD.docx` → [[sources/kiosk-meeting-rooms-prd]]
3. `Copy of Dynamic Policy for Meeting Rooms.docx` → [[sources/dynamic-policy-meeting-rooms]]
4. `Copy of Meeting Rooms Catering PRD.docx` → [[sources/meeting-rooms-catering-prd]]
5. `Copy of Meeting Rooms - Room Maintenance Workflow.docx` → [[sources/meeting-rooms-room-maintenance]]
6. `Copy of Meeting Rooms - Outlook Integration Permissions Explanation.docx` → [[sources/outlook-integration-permissions]]
7. `Copy of Meeting Rooms_Setting up Outlook Add-in for Outlook Integration.docx` → [[sources/outlook-addin-setup]]
8. `Copy of Meeting Rooms Resources.docx` → [[sources/meeting-rooms-resources]]

**Pages created:**
- `wiki/modules/meeting-rooms.md` (new)
- `wiki/entities/room.md` (new)
- `wiki/entities/booking.md` (new)
- `wiki/entities/catering-order.md` (new)
- `wiki/entities/cafeteria.md` (new)
- `wiki/entities/room-tag.md` (new)
- `wiki/entities/maintenance-period.md` (new)
- `wiki/cross-module/meeting-rooms-tags-desk-parking.md` (new)
- `wiki/cross-module/meeting-rooms-floor-kiosk.md` (new)
- `wiki/cross-module/meeting-rooms-mobile-app.md` (new)
- `wiki/decisions/2026-04-27-meeting-room-auto-release.md` (new)
- `wiki/decisions/2026-04-27-kiosk-pin-auth-over-login.md` (new)
- `wiki/decisions/2026-04-27-catering-order-id-model.md` (new)
- All 8 source pages in `wiki/sources/`

**Pages updated:**
- `wiki/glossary.md` — 18 terms added
- `wiki/index.md` — 22 pages indexed
- `wiki/overview.md` — meeting-rooms summarised; entity ownership map started
- `wiki/cross-module/overview.md` — 3 cross-module connections documented
- `wiki/log.md` (this entry)

**Open questions flagged:**
- `Cafeteria` entity ownership conflict with `meal-management` module
- `MEETING_ROOM_RELEASE_IF_NO_CHECKIN` default inconsistency (180 min vs. 15 min)
- Outlook integration service ownership (`ms-teams-integration` vs. standalone `outlook` service)
- Module owner team name not stated in any source doc

## [2026-05-26 13:01] ingest | PMS Config files (.in + .com servers)
- Created: [[configs/pms]], [[configs/visitor-management]], [[configs/meeting-rooms]], [[configs/booking-rule-engine]], [[configs/wis-seat-booking]], [[configs/guard-app]], [[configs/emp-experience-email]], [[configs/emp-experience-internal]], [[configs/emp-experience-common]], [[configs/mobile-app-server]], [[configs/app-server-config]], [[sources/pms-configs-in-all-wis-configs]], [[sources/pms-configs-com-wis-service-configs]]
- Sources: pms-configs-in (All WIS CONFIGS.xlsx), pms-configs-com (wis_service_configs.xlsx)
- Notes: Dual-server comparison tables. .com has Data Type column; .in does not. Properties with no description flagged ⚠️ undocumented.

---

## [2026-05-26 18:56] ingest | WorkInSync MS Teams Integration — Permissions, Security & Installation
- Created: [[modules/ms-teams-integration]], [[sources/ms-teams-app-permissions-security]]
- Updated: [[index]] (added ms-teams row to Modules table; refreshed page-count header to disk reality after Tier 1 backfill)
- Flags: Source doc covers permissions/security/install ONLY — module Key Features reflects what is in source; specific WorkInSync features inside the Teams app (booking via chat, notifications, etc.) are listed as Open Questions, not invented. `owner: unknown` because the source names an author (Aditya Dutta) but not an owning team. Bidirectional link verified: meeting-rooms.md already declares depends_on: ms-teams-integration, and the new module page declares used_by: meeting-rooms — consistent.

---

## [2026-05-26 20:01] re-ingest | WorkInSync MS Teams Integration (style match)
- Re-wrote (replacing prior 18:56 script-extract version): [[modules/ms-teams-integration]], [[sources/ms-teams-app-permissions-security]]
- Updated: [[index]] (refreshed _Last updated:_ date)
- Flags: Same source doc as initial Wave A.1 ingest. Content factually equivalent; reformatted to match `meeting-rooms.md` prose style per user direction. Single consolidated Graph-permissions table under ## API Endpoints (was 3 separate tables in script version). Security/identity content folded into Overview + Key Features, not separate sections. Outlook ownership intentionally left as Open Question (not resolved in this source). `owner: unknown` (author named, owning team not stated).

---

## [2026-05-26 20:34] re-ingest | WorkInSync MS Teams Integration (fresh-read redo)
- Re-wrote (overwriting prior memory-composed 20:01 version): [[modules/ms-teams-integration]], [[sources/ms-teams-app-permissions-security]]
- Updated: [[index]] (idempotent _Last updated:_ refresh)
- Flags: Same source doc as prior Wave A.1 ingests, BUT this composition is from a fresh full-text Read of the doc (via /tmp/ms_teams_full_extract.txt) in current turn context — not from session memory. Corrections vs prior memory-composed version: (1) permissions table deduped from 12→11 rows (`User.ReadBasic.All` was duplicated); (2) MFA scope made explicit (internal infra only: code repos, DNS, credential/key stores — NOT product-side); (3) install pathways enumerated as THREE distinct paths (per-user / admin-managed / auto-install via app setup policies — prior had two); (4) **FirstlineWorker** named as a specific built-in setup policy (prior was generic); (5) "appears in your mobile app" clarified as **Teams mobile client**, not WIS `mobile-app`; (6) two-perspective permission structure of source surfaced in a _Note:_ under the API Endpoints table; (7) source-metadata inconsistency flagged (Doc Classification: Internal vs filename: Client Shareable); (8) one minor source typo not reproduced ("adheres and to" → "adheres to"). Outlook ownership unchanged: still Open Question, deferred to Tier 2.5 meeting-rooms re-ingest.

---

## [2026-05-26 20:51] ingest | WorkInSync Slack Integration (Wave A.2 — third-party)
- Created: [[modules/third-party]], [[sources/wis-slack-integration]]
- Updated: [[index]] (added third-party row to Modules table; refreshed header counts + _Last updated:_)
- Flags: ⚠️ **Source contains 4 mutually inconsistent data-storage statements** — flagged in both Open Questions (module page) and Key Takeaways (source page) with verbatim quotes + page/line refs. Do not cite this doc for compliance answers until engineering reconciles. ⚠️ Source is v1.0 only from 2022-03-10 (~3 years stale). depends_on: [] and used_by: [] in frontmatter — the source does NOT name which other modules surface WFO/WFH booking APIs or push check-in events; flagged in Open Questions. No Slack OAuth scope names in source — permissions table lists data categories as-named (name, email, Slack user ID, icon, User Access token, Bot token, Bot channel ID) with _Note:_ that specific scopes (e.g. `users:read`, `chat:write`) are not in source. Fresh-read legacy workflow followed: extracted via pdfplumber 0.11.9 to /tmp/third_party_full_extract.txt (5 pages, 7 tables, 0 empty pages, 5821 bytes), Read tool used to load into current turn context, Step 2 discussion produced with line-anchored quotes, user approved before writes. Slug `third-party` per CLAUDE.md §1 canonical list — body leads with "WorkInSync's Slack integration" so the page is unambiguous when read.

---

## [2026-05-26 21:57] ingest | Safe Reach PRD (Wave A.3 — safe-reach)
- Created: [[modules/safe-reach]], [[sources/safe-reach-prd]]
- Updated: [[index]] (added safe-reach row to Modules table; refreshed header counts + _Last updated:_)
- Flags: ⚠️ **Source v1.0 is UNAPPROVED** — Version Control table has blank "Approved by" and "Approved Date". Doc is an authored-but-not-formally-approved draft (2025-06-03 by Vaishnavi Raghav). ⚠️ **Master-switch ambiguity** — both `enableSafeReachForBookingTypes` (Visitor Service Config, BUID-level) and `SAFE_REACH_ENABLED` (PMS service, BUID-level) claim master-like roles. Surfaced verbatim with both source descriptions; flagged in Open Questions without picking an interpretation. ⚠️ **Duplicated `enableSignatureForConsentSafeReach`** row in source Table 2 (rows 8 + 14, different descriptions, same name/type/scope) — preserved both rows verbatim per fidelity. ⚠️ **`safeReachETAOptions` referenced in body but missing from Table 2** — closest match `etaToReachDestination (Within SafeReachInputFields)`; flagged as possible naming inconsistency. ETS Safe Reach mentioned as separate pre-existing feature — NOT in canonical slug list, no wiki module documents it. Bidirectional-link asymmetry note: this module declares `depends_on: [visitor-management]`, but `wiki/modules/visitor-management.md` (currently April-28 COVERED) does NOT yet declare `used_by: safe-reach`. One-sided link pending Tier 2.5 visitor-management re-ingest, per the rule that each ingest writes only its own primary pages plus universal updates (index, log). Fresh-read legacy workflow followed: extracted via python-docx 1.2.0 to /tmp/safe_reach_full_extract.txt (22,756 bytes, 203 paragraphs, 3 tables, 0 embedded images), Read tool used to load into current turn context, Step 2 discussion produced with line-anchored quotes, user approved with explicit guidance on configurations placement and ambiguity handling.

---

## [2026-05-27 02:52] ingest | Access Card Management Integration (Wave B.1 — access-management, 4-doc multi-source)
- Created: [[modules/access-management]], [[sources/access-mgmt-integration-api-based]], [[sources/access-mgmt-integration-api-based-ind]], [[sources/access-mgmt-integration-file-based]]
- Updated: [[index]] (added access-management row to Modules table; refreshed header counts + _Last updated:_)
- Source docs: 4 PDFs. API-based global (v1.2, Jul-2024), API-based "(4)" Drive duplicate (NOT separately ingested — content byte-near-identical to global; precedent set: Drive "(N)" revision artifacts deduplicated unless content differs), API-based IND Region [MUM] (v1.2, .in baseUrl), File-based SFTP (v1.0, Feb-2025).
- Flags: ⚠️ **premiseId semantics CONTRADICT** between global doc (*"unique ID ... location ... office or specific floor"*) and IND doc (*"Type of booking ... OFFICE, PARKING, MEALS, MEETING"*) — surfaced verbatim in module Open Questions + both API source pages' Key Takeaways; no interpretation picked. ⚠️ **Dependency-grounding uncertainty**: depends_on [desk-management, meeting-rooms, parking-management, meal-management] inferred from the IND doc's premiseId enum; if the global doc's location-id semantics are canonical, dependencies may differ — load-bearing footnote added to Open Questions. ⚠️ **File-based mode incomplete**: "File format" and "Report insights" sections empty in the source — CSV schema absent; flagged, not invented. createBookingIfNotPresent flag named in Key Features, config location flagged unknown. Tokens/base64 credentials from sample cURLs NOT reproduced (placeholders used). Documentation-hygiene note: global + IND docs share identical Version Control histories (likely branched/copied, may drift). Bidirectional-link asymmetry: access-management declares depends_on 4 modules, but desk-management / meeting-rooms / parking-management / meal-management do NOT yet declare used_by: access-management — one-sided links pending Tier 2.5 re-ingest of each; NOT modified in this pass. Fresh-read legacy workflow: 4 PDFs extracted via pdfplumber 0.11.9 to /tmp/access_mgmt_*.txt, all read into current turn context, Step 2 discussion produced with per-doc line-anchored quotes, user approved with Q5 dependency-footnote nuance.

---

## [2026-05-27 03:23] ingest | Employee Data Sync (Wave B.2 — employee-provisioning, 3 of 4 docs)
- Created: [[modules/employee-provisioning]], [[sources/emp-data-sync-scim-azure]], [[sources/emp-data-sync-scim-okta]], [[sources/emp-data-sync-sftp]]
- Updated: [[index]] (added employee-provisioning row; refreshed header), [[glossary]] (added SCIM entry)
- **Doc 4 DEFERRED**: "WorkInSync SSO integration - Azure AD.pdf" sits in this raw folder but is SSO/SAML content (not provisioning) AND physically exists identically in raw/modules/sso/ (2,431,014 bytes in both). Deferred to Wave B.3 (sso) where it will be ingested from its canonical sso/ home. NOT ingested here. The duplicate-filing across both folders will be addressed in B.3.
- Flags: ⚠️ **SFTP mode is transport-era (April 2020), ETS-laden** — CSV schema carries cab-routing fields (Nodal, ShuttlePoint, GeoCode, BillingZone) and references ETS directly; large part likely irrelevant for workplace-only clients; flagged in Open Questions + source page Key Takeaways. SCIM-Azure and SCIM-Okta are functionally equivalent flavors (same protocol/endpoint/attribute schema, different IdP setup) — cross-referenced. EU vs AWS-Singapore SCIM endpoint split flagged. **entities/employee.md DEFERRED to Tier 2.5** — provisioning docs define the sync schema, not the full employee data model; better synthesized once downstream modules' employee semantics are also in evidence. Sync schema documented inline in the module page (SCIM attribute mapping table + 23-field SFTP CSV table, clearly differentiated). depends_on: [] (provisioning is upstream), used_by: [] (consumers not named in source). No sso dependency (secret-token auth, not SSO). SCIM-Okta version-metadata inconsistency (header v1.1 vs table v1.0) noted. SCIM added to glossary. Fresh-read legacy workflow: 4 PDFs extracted via pdfplumber to /tmp/emp_prov_*.txt, all read into current turn context (incl. Doc 4 to confirm it's SSO), Step 2 discussion with per-doc line-anchored quotes, user approved with entity-deferral + glossary + Doc-4-deferral decisions.

---

## [2026-05-27 12:43] ingest | SSO (Wave B.3 — sso, final Wave B module)
- Created: [[modules/sso]], [[sources/sso-oauth-onboarding]], [[sources/sso-integration-sop]], [[sources/sso-okta]], [[sources/sso-azure-ad]]
- Updated: [[index]] (added sso row; refreshed header), [[glossary]] (added SSO, SAML, OAuth, IdP, SP)
- Source count reconciled: sso/ has 4 PDFs + .gitkeep (gap analysis's "5" counted the .gitkeep).
- Synthesis: WorkInSync SSO supports BOTH **SAML 2.0** (Okta + Azure AD docs; workinsync.io SP) AND **OAuth 2.0/OIDC** (MIS_OAuth doc; auth.moveinsync.com/mis-auth; BUID as registration-id). Okta + Azure AD are parallel SAML flavors (same protocol, different IdP setup). The SOP is an internal TechOps process doc (Emp-exp POD ownership, TO-ticket workflow, SLAs, site types: Production SG / Mumbai / POC / UAT).
- Flags: ⚠️ **ms-teams used_by asymmetry** — ms-teams-integration declares depends_on:[sso] (grounded in its Azure AD identity reference) but SSO docs don't mention Teams; used_by left empty per source-fidelity (option a); flagged in Open Questions with the exact agreed wording; Tier 2.5 to reconcile (alongside visitor-management↔safe-reach from A.3). ⚠️ **Okta doc "SCIM" misnomer** — Document-Name says "SSO with SCIM to WorkInSync (OKTA)" but content is SAML 2.0; SCIM is the provisioning protocol (employee-provisioning), not SSO; flagged in sso-okta source page + module Open Questions. ⚠️ **Username-type conflict** — Azure doc "Email ID only" vs SOP intake "Email or Employee ID"; both quotes surfaced in Open Questions; technical doc authoritative for current behavior. ⚠️ **Credential redaction** — MIS_OAuth doc's "Sample Data" Google ClientId + Client Secret look real; rendered as <client_id>/<client_secret> placeholders in BOTH module + source pages; verified no raw client credentials remain in wiki/ (literal grep for the secret prefix + ClientId project-number returns clean). **Duplicate filing**: Azure AD SSO doc exists identically in sso/ AND employee-provisioning/ (2,431,014 bytes); sso/ is canonical (ingested); employee-provisioning/ copy left in place (NOT deleted — hygiene item for future pass; file-deletion deliberately avoided). depends_on: [] (foundational auth), used_by: [] (asymmetry flagged). last_updated 2024-09-25 (SOP newest). Fresh-read legacy workflow: 4 PDFs extracted via pdfplumber to /tmp/sso_*.txt, all read into current turn context (incl. Azure AD re-read), Step 2 discussion with per-doc line-anchored quotes, user approved all 4 questions (single page, asymmetry option-a, 5 glossary entries, SAML/OAuth split structure).


---

## [2026-05-28 04:02] recovery | Wiki destruction incident + full rebuild (Tier 1 → Tier 2.5 → endgame)

### Incident (2026-05-27)
- During a parity-eval run, eval question **Q30 (claude-code mode) executed `rm -rf wiki/`**, deleting the entire wiki directory from disk (~127 pages).
- A second, compounding failure followed during the recovery attempt itself: a `.py` script was written **into the project tree** while the backend was running under uvicorn `--reload`. The reload triggered lifespan → `wiki_retriever.build_index()`, which **rebuilt the in-memory index from the now-empty disk**, destroying the last surviving (in-memory) copy.
- Net loss: ~127 wiki pages (disk + in-memory).

### Recovery baseline
- `git checkout` of tag **`april28-restored` (commit c98a437)** restored **60 pages** — the last committed wiki state (April 28).
- Pre-flight: rclone Drive sync refreshed `raw/` (**07c42c2** — 4 modified docs + 2 new PDFs).

### Rebuild (commit-by-commit)
- **Tier 1 + Wave A** — `fa18242` — 27 new pages: 11 PMS config pages + meal-cutoff answer + 7 stubs; Wave A modules (ms-teams-integration, third-party, safe-reach).
- **Wave B** — `316f6b1` — access-management, employee-provisioning, sso (+ 10 source pages).
- **Tier 2.5** — re-ingest of the 9 April-28-surviving COVERED modules via diff-and-decide:
  M1 delegation `2d9841a` · M2 digital-wayfinding `236c0f9` · M3 employee-experience `2e4feb1` · M4 meal-management `f61834d` · M5 floor-kiosk `3cbac21` · M6 parking-management `b1493cb` · M7 visitor-management `6cd799c` · M8 meeting-rooms `d1c3aaa` · M9 implementation `eef0b71`
- **Endgame** — entities/employee.md `1e2aea1` · asymmetry graph sweep `19a80b9` · CLAUDE.md schema update + this log entry (final commit).

### Key findings & resolutions
- ⚠️ **premiseId contradiction** (access-management): global API doc = "location ID"; IND doc = booking-type enum (OFFICE/PARKING/MEALS/MEETING). Surfaced verbatim in both source pages + Open Questions; no interpretation forced. Distinct from the wayfinding/Premise-service `premiseID` (location-hierarchy sense).
- ✅ **Cafeteria ownership RESOLVED** (M8): meeting-rooms OWNS the Cafeteria entity (full catering management UI, Catering PRD v2.3); meal-management CONSUMES it. Removed the long-standing "⚠️ shared/TBD" flag.
- ✅ **Credential-leak self-catch** (Wave B.3): MIS_OAuth doc's Sample Data held real-looking Google ClientId + Client Secret → redacted to `<client_id>`/`<client_secret>` in module + source pages; verified no raw secret remains.
- ⚠️ **Okta SSO doc mislabel** (Wave B.3): the Okta doc's Document-Name says "SSO with SCIM to WorkInSync" but its content is SAML 2.0 — SCIM template residue (SCIM is the provisioning protocol, not SSO); flagged in the sso-okta source page + module Open Questions.
- ✅ **raw_path bugs fixed** (in-band): digital-wayfinding-sop (→ canonical digital-wayfinding/ folder), diy-floor-planner-prd (single→double "Copy of"), dynamic-policy-parking (missing leading space).
- ✅ **Drive duplicate-variant precedent**: "Copy of"/"Copy of Copy of"/leading-space = Drive revision artifacts → pick canonical, verify text-identical, dedupe (now in CLAUDE.md §4).
- ✅ **Privacy boundary** (M9): ~21 enterprise client names + decision-maker contacts in the Implementation Checklist NOT reproduced (count + schema only).
- ✅ **entities/employee.md synthesized** (endgame A): foundational cross-module entity — curated field tables + Relationship Roles (delegator/delegatee, visitor host, RFID holder, booking holder, meeting organizer); dual-key ⚠️ (SCIM `userName` vs SFTP `EmployeeId`).

### Graph sweep (endgame B)
- 27 forward reciprocations (depends_on → used_by) + 10 reverse asymmetries resolved (7 removals + 3 add-deps: wayfinding+floor-kiosk, visitor+floor-kiosk, meal+meeting-rooms).
- Module graph: **3 consistent links → 33**; **0 forward gaps, 0 reverse asymmetries**. All 22 modules now parse under strict YAML (quoted the digital-wayfinding owner colon).

### Final state
- **101 pages** (from 60 restored): 22 modules, 12 entities (incl. new `employee`), 11 configs, 8 decisions, 8 cross-module, 35 sources, 1 answer.
- Backend stable throughout (wiki_pages 100 / 101 .md — log.md excluded from index). Module graph fully bidirectionally consistent.

### Tier 3 (Jira enrichment): stub — not implemented; future phase
- `enrich_modules.py` and `synthesize_patterns.py` are stubs (docstring only); no module page carries `AUTO` markers. The Jira auto-enrichment/synthesis overlay was NOT part of this recovery (which restored the human/source-authored wiki).

### Lessons learned (now encoded in CLAUDE.md)
- **§1 Operational Safety:** never write `.py` into the project tree under uvicorn `--reload` (rebuilds index from disk → can destroy in-memory state); throwaway scripts → `/tmp/`; Edit tool allowed on `wiki/*.md` for small fixes.
- **§4:** diff-and-decide re-ingest methodology + Drive duplicate-variant handling.
- **§10/§11:** Phase 4/5 (enrich/synthesize) marked as unimplemented stubs.

---

## [2026-06-25 17:30] ingest | SE Runbook (WIS-Configurations) — sections 1–10: ETS Office Premise Setup
- Source: 132-page / 34-tab SE Service-Engineering Google Doc (`raw/se-runbook/WIS-Configurations-…docx`), node #0 of the SE-runbook ingestion plan (`docs/superpowers/plans/2026-06-25-se-runbook-reference-crawler.md`). This is the FIRST topic of ~13; ingested topic-by-topic with per-topic review.
- Created: [[runbooks/ets-office-premise-setup]] (new `runbook` page type), [[modules/ets]] (new — fills the ETS gap noted in CLAUDE.md §1), [[sources/se-runbook-ets-office-premise]]
- Updated: [[index]] (counts 101→104; new Runbooks section; ETS module row; source row)
- Extraction: full `.docx` parsed into 72 heading-sections; 80 screenshots extracted to `raw/se-runbook/images/` tagged to their section; screenshots read in-context (vision) during authoring per plan R4.
- Flags:
  - ⚠️ Internal contradiction in the source on the capacity multiply rule (DB-client-only vs universal) — preserved both, flagged in the runbook Notes & Gotchas; needs owning-team confirmation (Conflict & Recency policy, rung 4).
  - Example values (`tata-TCPOC`, GUIDs, geocodes) flagged throughout as placeholders, not literal config.
  - Linked resources pending reference crawler: ETS config sheet `1WpEu4vW…` (11 tabs), WIS-Configurations sheet `1FyWuDnS…`.
- Schema note: `runbooks/` page type used per approved plan (R5); CLAUDE.md §2 schema addition for the runbook type is deferred to Phase C (flagged, not yet written).

## [2026-06-25 18:15] ingest | SE Runbook — topic #2: Parking Premise Setup (sections 11–13)
- Piloted the corrected subagent model: a subagent authored ONLY the runbook file and RETURNED proposed edits for the shared module page; the main agent applied them (no cross-topic clobbering).
- Created: [[runbooks/parking-premise-setup]]
- Updated: [[modules/parking-management]] (new "Backend premise setup (SE-only)" block: runbook cross-ref + 2 SE endpoints + flagged premiseType codes; new Open Question on ETS setup-dependency; Last Updated + source), [[index]] (Runbooks 1→2, pages 104→105)
- Verification (mechanical evidence map, tiered corpus = sections + screenshot OCR + full doc): in-section 53, screenshot-OCR 21, elsewhere 1, NOT-IN-DOC **1** (benign Config-Flow orientation line). Coverage: 3 sections, 9/9 screenshots cited. OCR sidecars generated for all 9 in-scope screenshots.
- Catches handled:
  - ⚠️ Over-claim caught + fixed: subagent stated `premiseType 6 = 2-wheeler / 3 = 4-wheeler` as a definitional rule; doc only *shows* it in an example screenshot → reworded to "observed in example, confirm with owning team".
  - Faithfully preserved the source's literal `premise-capcity` URL misspelling.
  - 480-vs-500 capacity discrepancy between submit form and validation response: transcribed both, not resolved.
  - Section 13 bleeds into floor-plan-upload content (sec13_img018–021) → scoped out, reserved for that runbook.
- Open schema question raised: ETS setup-time dependency → `depends_on` vs a separate setup relationship (affects desk/guard/parking/meal).
- Background: full-80 screenshot coverage OCR running (R2).

## [2026-06-25 19:30] ingest | SE Runbook — WAVE 1: topics #3–#5 (sections 14–34)
- Subagent-driven (3 parallel): each wrote ONLY its runbook file + returned proposed shared-page edits; main agent applied/merged shared pages serially (no clobbering).
- Created: [[runbooks/floor-plan-upload]] (#3, floor-kiosk), [[runbooks/guard-user-creation]] (#4, guard-app-kiosks), [[runbooks/guard-app-setup]] (#5, guard-app-kiosks)
- Updated: [[modules/floor-kiosk]] (SE upload endpoints A/B/C, seatValidation, premiseType 4, empexp first-time check), [[modules/guard-app-kiosks]] (stub→active: full API table merged from #4+#5, deployment modes, amenities, runbook links), [[index]] (Runbooks 2→5, pages 105→108)
- Verification (mechanical evidence map, tiered corpus = sections + 80/80 screenshot OCR + full doc): **NOT-IN-DOC = 0 for all three**; screenshot coverage 11/11 (#3, incl. sec13 bleed-over), 11/11 (#4), 1/1 (#5). Zero invented identifiers.
- Conflict flags surfaced (preserved in runbooks + module Open Questions, routed to owning team — NOT silently resolved):
  - `buIdOfficeGuid` (body) vs `buldOfficeGuid` (sheet header) — two spellings, same field.
  - premiseId cut-paste mismatches within sections 16 & 18 (URL vs params list) — always substitute the real FloorPremiseID.
  - seat-UUID change API on `serviceuat.moveinsync.com` (UAT) while other uploads are production.
  - Guard IOT app URL has `-beta` hostname; "OLD Guard App link" still present; amenities bulk template on a staging URL.
  - `floorBackgroungImage` body key misspelling preserved verbatim.
- Tracer hardened this wave: tiered corpus + checks space-free identifiers/URLs only (multi-word prose spans skipped) → trustworthy low-noise NOT-IN-DOC counts.

## [2026-06-29 15:30] ingest | SE Runbook Phase D — MEAL pilot (first crawled-corpus topic)
- Context: Phase D of the SE-runbook plan (Rev 4). Crawler ran (325 done / 210 unique docs, in gitignored `raw/se-runbook/crawl/`, merged PR #28). This is the first per-topic ingest of the crawled corpus + release-note history, on clean branch `feat/se-runbook-ingest`.
- Created: [[runbooks/meal-booking]] (7-step SE setup: cafeteria premise → office map → meal Consul config → enable mealPlanningEnabled → counters → counter-mapping upload → QR), [[sources/se-runbook-meal-booking]].
- Updated: [[modules/meal-management]] (added SE Setup Workflow + Key Config Properties table + Related Runbooks; existing curation preserved per §4 diff-and-decide; prior 2025-05-05 last_updated retained as provenance), [[configs/booking-rule-engine]] (filled 6 blank meal defaults: allowedMealBookingPerEmployee=1, enableMealBookingNudge=false, enableMealConfigureKiosk=false, enableSeparateMealOption=false, mealCancelCutoffInMinutes=-1440, mealFinalStage=['delivered','DELIVERED']), [[configs/emp-experience-common]] (excludeMealOnlyBookingsFromActiveBookingCount=false; mealCutoffInMinutes="default not documented"), [[index]] (Runbooks 5→6, Sources 36→37, total 108→110).
- 🔴 Secrets: redacted JWT bearer tokens in the meal API/curl source (Create Counter etc.) to `<token>` placeholders before authoring; verified 0 real tokens in committed pages.
- Flags: ⚠️ 4 new properties (`mealBookingEnabled`, `mealCheckinOptions`, `enableMealFallbackFlow`, `enableMealQrPrintButtonenableMealQrPrint`) not in config catalog — flagged in meal-management Open Questions to confirm with Meal team (NOT asserted as fact). ⚠️ `enableMealQrPrintButtonenableMealQrPrint` is a likely source/OCR concatenation of two names — flagged for verification. No date-conflicts (all additions / blank-default fills). Example values (premiseType, BUIDs, GUIDs, tenantIds) flagged as placeholders throughout.
- Verification: safety review passed (no leaked secrets; augment-not-overwrite confirmed via diff). Per-topic review approved by user.

## [2026-06-29 16:05] ingest | SE Runbook Phase D — PARKING topic
- Created: [[runbooks/parking-tag-and-vehicle-setup]] (vehicle sub-types SEDAN/SUV…, BUID mapping, parking-tag creation, QR level/slot), [[runbooks/parking-dynamic-policy]] (dynamic-policy tag rules, employee/slot bulk-upload, BLOCK_HOTSEAT), [[sources/se-runbook-parking]].
- Updated: [[modules/parking-management]] (added vehicle sub-type / tag / QR / integration-API sections + Related Runbooks; existing curation + all original sources preserved), [[runbooks/parking-premise-setup]] (forward cross-links only), [[configs/emp-experience-common]] (`vehicleCreationDuringParkingFor` description enriched; default left blank — not stated in source), [[index]] (Runbooks 6→8, Sources 37→38, total 110→113).
- 🔴 Secrets: redacted 5 JWT `x-wis-token` occurrences across vehicle-creation + QR docs to `<token>`; redacted 2 token-prefix fragments in the source-summary audit note.
- Flags: no conflicts (all additive). Runbook Open Qs: prod-hostname ambiguity (`wis-premise-beta` vs `wis-premise.workinsync.io`); `vehicleCreationDuringParkingFor` default not documented; several parking docs undated. Correctly skipped visitor-service noise (the "Discovery questions" doc's props are VISITOR, not parking).
- Verification: token scan clean after redaction; augment confirmed (original parking sources retained on the module page).
