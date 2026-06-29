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

## [2026-06-29 16:40] ingest | SE Runbook Phase D — SANITIZATION topic (NEW module)
- Created: [[modules/sanitization]] (NEW module — seat sanitization: HOUSEKEEPER QR-scan cleaning, cut-off; + a Vaccination Status section; status active; depends_on [desk-management, guard-app-kiosks]), [[runbooks/seat-sanitization]] (NEW runbook — HOUSEKEEPER user creation, QR-scan enable/disable, sanitize cut-off, from the main-doc SE sections), [[sources/se-runbook-sanitization]].
- Updated: [[index]] (Modules 23→24, Runbooks 8→9, Sources 38→39, total 113→116).
- Sources: 12 main-doc sanitization sections (core SE procedure) + 9 crawled docs. 7 sanitization/vaccination config props documented in the module's config table (`SANITISATION_STATUS_ENABLED`, `enableQrCodeForSeatSanitize`, `seatSanitizeCuttoffInMinute`, `vaccinationBookingEnabled`, `showVaccinationOptionInSideMenu`, `blockUserIfNotVaccinated`, `vaccinationMaxApprovalDays`).
- 🔴 Secrets: subagent EXCLUDED a live JWT in main-doc section 59 (a meeting-room onboarding curl, not sanitization) rather than import-then-redact → 0 tokens in deliverables (verified).
- Flags: ⚠️ module-placement (standalone `sanitization` vs fold into desk-management/guard-app-kiosks) flagged in Open Questions — not forced. ⚠️ reciprocal `used_by` on desk-management/guard-app-kiosks pending graph-consistency sweep. ⚠️ `seatSanitizeCuttoffInMinute` name implies DOUBLE but source shows boolean — flagged for the team. ⚠️ vaccination may warrant its own module — flagged. Example values (BUID `eu-TestBed`, HOUSEKEEPER `Jovil`/phone, role:"3"→WORKER) flagged as placeholders.
- Verification: token scan clean; all-new content (no overwrite); per-topic review pending user.

## [2026-06-29 17:10] ingest | SE Runbook Phase D — ETS topic (filled the central stub)
- Updated: [[modules/ets]] (**stub → active**: full Overview/Purpose/Key Features/Data Entities/API Endpoints/ETS Configs/Open Questions; used_by extended desk+guard+parking → +meal +floor-kiosk; original office-premise facts preserved + expanded; **source frontmatter restored to cite BOTH se-runbook-ets + se-runbook-ets-office-premise** after author had replaced it). [[index]] (ets row stub→active; Runbooks 9→10; Sources 39→40; total 116→118).
- Created: [[runbooks/ets-data-sync]] (ETS→WIS employee data sync — SFTP/API channels, TechOps ticket fields, SLA tiers, P0 escalation), [[sources/se-runbook-ets]].
- ETS configs captured: `indemnifyOfficeBookingTransport` (BOOLEAN, default false, Jira-only PB-52960), `commuteMandatory` (example true), `showCabs` (correctly attributed to BookingRuleEngine, NOT ETS service) + indemnification-feature flags. Closes part of the CLAUDE.md §1 "ETS configs are Jira-only" gap.
- 🔴 Secrets: redacted 1 RS256 JWT in the API auth doc → `<token>`. 0 tokens in deliverables.
- Cross-linked (NOT duplicated): SCIM/employee-sync → [[modules/employee-provisioning]]; meeting docs → [[modules/meeting-rooms]]; SSO → [[modules/sso]]; face-recognition → floor-kiosk/guard. Filtered heavy "data sync" keyword noise.
- Flags: ⚠️ ETS setup-time vs runtime dependency direction unresolved — reciprocal depends_on on the 5 consuming modules deferred to graph-consistency sweep. ⚠️ owner unknown; indemnify/commute/showCabs defaults not documented (Jira-only). Example values (office GUIDs, BUIDs) flagged as placeholders.
- Verification: token scan clean; stub-fill preserved+expanded original facts (office API, GUID reference retained); source provenance restored.

## [2026-06-29 17:45] ingest | SE Runbook Phase D — ACCESS-MANAGEMENT topic
- Created: [[runbooks/access-card-integration]] (SE setup — REST vendor onboarding + auth/token flow + endpoints; SFTP file-based mode; check-in-mode value reference; troubleshooting), [[sources/se-runbook-access-card]].
- Updated: [[modules/access-management]] (enriched Key Features + SE Setup Workflow + config table + Related Runbooks; existing API/SFTP content reworded+expanded, NOT lost; all 3 original sources preserved + se-runbook-access-card added), [[configs/booking-rule-engine]] (8 check-in props filled), [[configs/emp-experience-common]] (`lastSwipeAsCheckoutTimeForBUID` default-filled), [[index]] (Runbooks 10→11, Sources 40→41, total 118→120).
- 🔴 Secrets: redacted 3 credentials (1 base64 client_id:client_secret + 2 JWT samples) → `<bearer-token>`/`<base64(...)>`. Confirmed 0 `eyJ…` in any page.
- Config notes: `defaulBookingHoursIfExtCheckin` typo preserved verbatim. Defaults `false` where source documents opt-in flags; `defaulBookingHoursIfExtCheckin`/`extCheckinToBookingBuffer`/`officeCheckInModeWeb/App`/`lastSwipeAsCheckoutTimeForBUID` marked "not documented" (source states no default).
- Flags: no conflicts (officeCheckInMode values had no prior wiki entry). Open Qs: SFTP swipe-CSV column schema not in source; `lastSwipeAsCheckoutTimeForBUID` LIST syntax unconfirmed; pre-existing premiseId semantic open-question preserved.
- Verification: augment confirmed (reworded-not-lost; sources preserved); token scan clean; config fills in-place (meal rows untouched).

## [2026-06-29 18:15] ingest | SE Runbook Phase D — EMPLOYEE-PROVISIONING topic
- Created: [[runbooks/employee-data-sync-scim]] (SCIM provisioning setup for Azure AD / Okta + SFTP CSV mode + troubleshooting from the Internal guide; scoped to protocol/IdP, cross-links ets-data-sync for the ETS process), [[sources/se-runbook-employee-provisioning]].
- Updated: [[modules/employee-provisioning]] (enriched SCIM 2.0 detail, IdP attribute mapping, Stratus data-sync API, role/privilege mgmt; 129→227 lines; 3 original sources preserved + new appended; last_updated → 2025-03-06 = newest source doc date per diff-and-decide), [[index]] (Runbooks 11→12, Sources 41→42, total 120→122).
- Overlap handling: ets-data-sync (ETS TechOps process) vs this (SCIM/SFTP protocol + IdP setup) — cross-linked 5×, not duplicated; ambiguity (2025 Stratus Direct API vs older ETS API) flagged in Open Questions.
- 🔴 Secrets: the 1 doc with a real JWT (PB-22330 sender-email) was off-topic noise → excluded entirely (not ingested). 0 `eyJ…` in any page.
- Config: provisioning is protocol-level — no PMS config properties documented (none filled).
- Flags: Open Qs — SCIM secret-token expiry not documented; IdP group→WIS-group mapping not supported; Stratus role API endpoints not in provisioning docs. Cross-linked noise: visitor-bulk-upload→visitor, meeting→meeting-rooms, MS-Teams→ms-teams, SSO→sso.
- Verification: token scan clean; augment (+98 lines, sources preserved).

## [2026-06-29 18:45] ingest | SE Runbook Phase D — FLOOR-KIOSK topic
- Created: [[runbooks/floor-kiosk-device-setup]] (Android/iPad kiosk enrollment in Scalefusion MDM — afw#mobilock + APK methods, iPad variants, RemoteCast, post-enrollment checklist; cross-links floor-plan-upload + meeting-rooms), [[sources/se-runbook-floor-kiosk]].
- Updated: [[modules/floor-kiosk]] (dual-source Hardware Specs comparison + Unsupported-HW table, Scalefusion MDM section, Employee-Flow kiosk, Self-Checkin tablet flow; 3 original sources preserved + new appended; last_updated → 2026-02-02 = Spec Sheet date), [[configs/visitor-management]] (augmented `isEmployeeFlowEnabled`, `DefaultEndTimeOfEmployeeBooking`=1439, `visitorFormsMetaData`, `visitorKioskConfigs` — these live in VISITOR service; manual-notes marker block added), [[index]] (Runbooks 12→13, Sources 42→43, total 122→124).
- Conflicts (dual-claimed ⚠️, not silently resolved): GPU min Adreno 619 vs 640; CPU freq spec mismatch; `visitorFormsMetaData` "Not in use" (auto-gen) vs active SE usage; `isEmployeeFlowEnabled` standalone-PMS-row vs sub-key of `visitorKioskConfigs`.
- 🔴 Secrets: 0 (none in source; enrollment codes/QRs were blank placeholders).
- Flags: device naming convention only has an MR-kiosk example (flagged); meeting-room-kiosk Scalefusion content cross-linked to meeting-rooms, not duplicated.
- Verification: token scan clean; augment (sources preserved; config fills in-place, other props untouched).

## [2026-06-29 17:05] ingest | SE Runbook — Digital Wayfinding topic (Phase D)
- Created: [[runbooks/digital-wayfinding-setup]], [[sources/se-runbook-digital-wayfinding]]
- Updated: [[modules/digital-wayfinding]] (enriched 75→214 lines: value/use-case, product-architecture ASCII reconstruction w/ caveat, DIY Floorplanner table, API endpoints), [[index]] (counts 124→126, Runbooks 13→14, Sources 43→44)
- Source docs: Digital Wayfinding SOP + SE-runbook crawl (Conwo WorkInSync Docs Drive)
- Flags: product-architecture diagram is a reconstruction from SOP screenshots/text — marked with caveat. `ENABLE_INDOOR_NAVIGATION` default not stated in source (left blank pending confirm). Token scan: CLEAN (no secrets in source).

## [2026-06-29 17:35] ingest | SE Runbook — Desk Management topic (Phase D) — STUB → ACTIVE
- Created: [[runbooks/desk-booking-setup]], [[runbooks/recurring-booking-setup]], [[runbooks/booking-approval-camunda]], [[sources/se-runbook-desk-management]]
- Updated: [[modules/desk-management]] (stub→active, 69→141 lines; all §2a sections filled; depends_on: [tags-desk-parking]; used_by preserved; 4 API endpoints from 2024 Booking API doc), [[index]] (added missing desk-management Modules row; counts 126→130, Runbooks 14→17, Sources 44→45)
- Sources: 6 docs (Booking API 2024, Recurring Booking, MODULE 2 Desk Booking overview, Desk Allocation xlsx, Booking Approval Camunda, Perpetual Digi Pass 2021 pptx)
- Config properties: 19 documented (BOOKING-RULE-ENGINE ×3, EMP-EXP-COMMON-CONFIG ×1, WIS-SEAT-BOOKING ×15) — no defaults stated in source; captured as open questions
- Secrets redacted: 2 RS256 JWTs (pre-redacted), Basic-auth base64 credential → `<base64(username:password)>`, internal email userId → `<userId>`, Camunda demo creds omitted; controller also scrubbed credential fragment + real email from source-summary disclosure prose
- Flags: ⚠️ Perpetual Digi Pass doc is 2021 historical only (current enablement unverified) — Previously-note + open question. Graph sweep TODO: `sanitization` lists desk-management in depends_on but desk-management used_by omits it; `implementation` reciprocal unconfirmed; consider new [[entities/desk]] page; `booking-rule-engine` has no module page (config-only).

## [2026-06-29 18:05] ingest | SE Runbook — Tags-Desk-Parking topic (Phase D) — STUB → ACTIVE
- Created: [[runbooks/tag-and-dynamic-fields-setup]], [[sources/se-runbook-tags-desk-parking]]
- Updated: [[modules/tags-desk-parking]] (stub→active; all §2a sections filled; depends_on: []; used_by += desk-management → [meeting-rooms, parking-management, desk-management] — closes desk-management reciprocity), [[index]] (added missing tags-desk-parking Modules row; counts 130→132, Runbooks 17→18, Sources 45→46)
- Sources: 4 docs (Parking Tag Creation, Tagging&DynamicFields curl, SeatTypeMapping xlsx, + 1 bundled visitor doc EXCLUDED). Existing parking runbooks (parking-tag-and-vehicle-setup, parking-dynamic-policy) linked, not duplicated.
- Config properties: 3 Consul-backed dynamicFields (DynamicData, transport, licenseNo on wisSeatBooking) — NOT PMS xlsx props; no defaults stated
- Secrets redacted: HS512 x-wis-token JWTs (pre-redacted), example BUID UUID → <BUID>
- Flags: ⚠️ Doc 4 (businessGuests/contractor/deliveryPersonnel) is VISITOR-management dynamic-fields config bundled by mistake — needs separate visitor ingest (NOT modelled here). SeatTypeMapping upload mechanism undocumented. Beta host wis-seat-beta.moveinsync.com in source — confirm prod URL. Graph sweep: room-tag entity used_by should add desk-management + parking-management.

## [2026-06-29 12:45] ingest | SE Runbook — Meeting Rooms (Phase D)
- Created: [[runbooks/meeting-room-setup]], [[runbooks/meeting-room-catering-setup]], [[runbooks/outlook-room-integration]], [[sources/se-runbook-meeting-rooms]]
- Updated: [[modules/meeting-rooms]] (appended [[sources/se-runbook-meeting-rooms]] to source: frontmatter; added ## Related Runbooks section before ## Open Questions — no other prose changed), [[index]] (counts 132→136, Runbooks 18→21, Sources 46→47; added 3 runbook rows + 1 source row)
- Config properties confirmed by SE sources: MEETING_ROOM_RELEASE_IF_NO_CHECKIN recommended=15min (module page already had this — SE doc confirms operational recommendation); new surface: ALLOW_ONLY_ONE_MEETING_ROOM_AT_ONCE, BOOK_MEETING_ROOM_BY_EMPLOYEES, SHOW_SPECIAL_REQUEST_ON_MEETING, ENABLE_REMINDER_NOTIFCATION (typo preserved), RELEASE_MR_NOTIFICATION, ENABLE_NEXT_MEETING_REMINDER
- Secrets redacted: none (source material scanned clean)
- Flags: ⚠️ Outlook Pre-Impl Discovery is a 2021 document — outlook-room-integration.md marked stale; all consent-URL/endpoint details need verification against current wis-integration service before client engagement. ⚠️ cateringLimits is .com-only — .in clients cannot configure participant-count cut-offs. ⚠️ Control doc is 52k chars; only first ~13k captured in SE crawl input — exhaustive acceptance criteria not modelled.

## [2026-06-29 19:15] ingest | SE Runbook Phase D — VISITOR-MANAGEMENT (VMS) topic
- Created: [[runbooks/visitor-badge-printer-setup]], [[runbooks/visitor-bulk-upload]], [[runbooks/visitor-notifications-setup]], [[runbooks/visitor-custom-fields-setup]], [[sources/se-runbook-visitor-management]]
- Updated: [[modules/visitor-management]] (appended [[sources/se-runbook-visitor-management]] to `source:` frontmatter string; added `## Related Runbooks` section before `## Open Questions` — no other prose changed; `last_updated` NOT changed, preserved as 2023-07-11), [[configs/visitor-management]] (added "Notification Setup Notes" subsection in MANUAL NOTES block with `PrivilegeConfigurations_Visitor_Management_Notifications` — only genuinely-missing property from SE docs; all other SE-referenced properties already exist in auto-gen table), [[index]] (header counts 136→141; Runbooks 21→25; Sources 47→48; added 4 runbook rows + 1 source row — no new Modules row, visitor-management already present)
- Config properties confirmed by SE sources: `BULK_OPERATION_VISITOR_BOOKING` (Consul-backed); `enabledBuidForVisitorConfigs` (master opt-in for property-controlled notifications); `notificationMetaData` / `notificationConfigs` (grouping+ID consistency rule confirmed); `hostNotifications` / `creatorNotifications` / `externalNotifications` (per-persona routing, externalNotifications=.com only); `formsMetaDataForWalkIn` (walk-in custom fields + Belongings cross-flow rule); `formsMetaDataForHostPWC` (invited-flow host fields + bulk-upload custom columns); `profileFieldsMetaData` ↔ `visitorBulkUploadData` key-matching gotcha confirmed; `visitorFormsMetaData`/`dynamicFields` per-visitor-type schema (hideOnWalkin, enableStandardWalkinVisitorForm)
- Secrets redacted: none (source material scanned clean; `agilos.workinsync.io` is a tenant URL, not a credential)
- Flags: ⚠️ Doc 1 (Visitor Management — Configuration 2024) text extract captured badge-printer specs only — full office-config enablement steps are in screenshots not captured by SE crawl. Runbook 1 faithfully covers printer hardware; see raw file for visual SOP. ⚠️ Doc 5 (DynamicFields JSON) is truncated at ~12.5k of 14.7k chars — `personalGuest` visitor type not captured; verify complete schema with owning team. ⚠️ Doc 5 was misfiled in tags-desk-parking batch (excluded there per 2026-06-29 18:05 log entry) — now correctly re-homed under visitor-management. ⚠️ `visitorFormsMetaData` auto-gen "Not in use" conflict (pre-existing, from floor-kiosk ingest) carried forward — SE custom-fields doc confirms active use; owning-team verification still needed.

## [2026-06-29 20:30] ingest | SE Runbook — KIOSK topic (Phase D)
- Created: [[runbooks/meeting-room-kiosk-setup]], [[sources/se-runbook-kiosk]]
- Updated: [[modules/guard-app-kiosks]] (added §Production vs Beta Backend Endpoints table; updated Key Features note to clarify backend host confirmed; updated Open Questions to distinguish backend (confirmed) from front-end IOT URL (still open); appended `[[sources/se-runbook-kiosk]]` to `source:` frontmatter; bumped `last_updated` to 2026-06-29), [[modules/meeting-rooms]] (appended `[[sources/se-runbook-kiosk]]` to `source:` frontmatter; added `[[runbooks/meeting-room-kiosk-setup]]` bullet to §Related Runbooks — no other changes, `last_updated` NOT changed, preserved as 2024-03-12), [[index]] (header counts 141→143; Runbooks 25→26; Sources 48→49; added 1 runbook row + 1 source row — no new Modules row)
- Source docs: 3 docs — Prod URL reference (backend service endpoints), Meeting Room Kiosk Setup Control Document (v1.1, 2022-10-21), Meeting Room Kiosk Scalefusion Prerequisites
- Endpoint confirmed: `mis-security-guard` PROD = `wis-premise.workinsync.io/mis-security-guard/`; Beta = `mis-security-beta1.moveinsync.com/mis-security-guard/`; EU-Green = `mis-security-green.eu.moveinsync.com/mis-security-guard/`
- Secrets redacted: none (source material scanned clean; all URLs are service hostnames, not credentials)
- Flags: ⚠️ Doc 1 confirms BACKEND service host only — front-end IOT Guard App URL question (the `-beta` hostname ambiguity) remains open. ⚠️ Control Document (Doc 2) is dated 2022-10-21 v1.1 but referenced in the SE crawl batch as "2025" — content treated as current SE procedure; verify kiosk URLs per-client as the team may have updated them. ⚠️ Scalefusion QR codes for meeting-room kiosk vs floor kiosk are different — must not be mixed; this gotcha is documented in the runbook. Graph sweep TODO: confirm bidirectionality — [[modules/floor-kiosk]] does not have `used_by: [meeting-rooms]` but meeting-room-kiosk-setup references the floor-kiosk runbook as a shared procedure; assess whether a `depends_on` relationship is warranted.

## [2026-06-29 00:00] ingest | MS Teams Integration — Control Document (v1.1, 2022-06-20) + CS/Sales Universe Index
- Created: [[runbooks/ms-teams-integration-setup]], [[sources/se-runbook-ms-teams]]
- Updated: [[modules/ms-teams-integration]] (AUGMENTED — added `## Onboarding Pathways` section; added `## Features Exposed in Teams` section covering employee features, people-manager features, bot commands table, and personal+team tabs; updated Open Question #1 from fully-open to partially-resolved with ⚠️ staleness caveat; appended `[[sources/se-runbook-ms-teams]]` to frontmatter `source:` string; `last_updated` preserved at `2024-01-08` — NOT changed), [[index]] (header counts 143→145; Runbooks 26→27; Sources 49→50; added 1 Runbooks row + 1 Sources row — no new Modules row, no new Entities/Configs/Decisions rows)
- Source docs: 2 docs — (1) CS/Sales App Universe index (navigation/index only, low content; treated as sales source-of-truth pointer); (2) MS Teams Integration Control Document v1.1 (2022-06-20, rich operational doc covering prerequisites, two onboarding pathways, install/consent flows, license management, feature set, bot commands, tabs)
- Secrets redacted: NONE — source material scanned clean. `xyz@workinsync.io` is a placeholder example in the doc, not a credential.
- Flags: ⚠️ Primary source is dated 2022 (v1.1, 2022-06-20) — feature list, bot commands, tab structure, pricing plans, consent UX, and onboarding landing-page flow should be verified against current product before client-facing use. ⚠️ Open Question #1 on ms-teams-integration partially resolved (features/bot/tabs now documented) but staleness of 2022 content means current feature set is still unverified. ⚠️ Free plan cap (≤50 users) and Standard/Professional feature-gating detail still defers to "WiS Pricing Page" — not reproduced in source. Graph sweep TODO: [[modules/desk-management]] and [[modules/employee-experience]] are implicitly involved (desk booking + WFH check-in via Teams) — assess whether a cross-module or `used_by` link is warranted.

## [2026-06-29 21:00] ingest | SE Runbook Phase D — SSO topic
- Created: [[runbooks/sso-integration-setup]], [[sources/se-runbook-sso]]
- Updated: [[modules/sso]] (AUGMENTED — added `## Related Runbooks` section before `## Open Questions`; appended `[[sources/se-runbook-sso]]` to frontmatter `source:` string; softened "OAuth doc is undated" open question with note that 2024 Complete Guide exists but is SAML-only; `last_updated` preserved at `2024-09-25` — NOT changed; all other prose, Integration Surfaces section, and prior open questions untouched), [[index]] (header counts 145→147; Runbooks 27→28; Sources 50→51; added 1 Runbooks row + 1 Sources row — no new Modules row, no new Entities/Configs/Decisions rows)
- Source docs: 2 docs — (1) MoveInSync Web Single Sign-On Complete Guide v1.2 (30/04/2024, SAML/Azure AD; authors: Arun/Nitin Awasthi/Shruthi Naik; approved Bhargav G); (2) Login seamlessly on MoveInSync app via SSO (mobile pptx, undated)
- Secrets redacted: NONE — both source documents scanned clean. No OAuth client_secret, no GOCSPX-* tokens, no X509 cert blocks, no JWT/Bearer tokens, no real email addresses. Existing [[modules/sso]] OAuth section already uses <client_id>/<client_secret> placeholders from prior ingest.
- Flags: ⚠️ USERNAME-TYPE EVOLUTION — 2024 Complete Guide (v1.2) explicitly lists BOTH "Email ID" and "Employee ID" as supported username types. This contradicts the older Azure AD PDF ("Email ID only, Employee ID not supported") that underlies the existing username-type open conflict in [[modules/sso]]. The 2024 guide is the newer and more authoritative source. Module page open question updated to note this; Integration Surfaces line ("Username type: Email ID") should be reviewed by module owner. The runbook captures this as a gotcha and defers winner selection to the TO team. ⚠️ last_updated rationale: 2024 Complete Guide is dated April 2024 (30/04/2024 = DD/MM/YYYY confirmed by v1.0 date 24/02/2022) which is OLDER than the module's current 2024-09-25 — KEPT. ⚠️ OAuth-undated question NOT resolved — the 2024 guide is SAML/Azure AD only; MIS_OAuth_OnBoarding.pdf freshness still unknown. ⚠️ SP metadata ACS URLs in the runbook (accounts.moveinsync.com) may differ in role from the module's Integration Surfaces `<client>.workinsync.io` per-client SP domain — not contradicted, but the relationship between the two URL patterns was not explained in the 2024 source; flagged as potential open question for graph sweep.

## [2026-06-29 21:10] controller-edit | SSO username-type recency resolution
- Updated: [[modules/sso]] — converted the "Username-type conflict" open question to a Current(2024)/Previously(2023) recency resolution. The 2024 Web SSO Complete Guide (v1.2, 2024-04-30) supports BOTH Email ID and Employee ID, superseding the older 2023 Azure doc's "Email-ID-only". Applied per Conflict & Recency ladder (newer dated source wins). Left a ⚠️ note that the Integration Surfaces SAML line still reads "Email ID" — deferred to graph/recency sweep.

## [2026-06-29 21:40] ingest | SE Runbook — Third-Party (Slack) topic (Phase D)
- Created: [[runbooks/slack-workspace-install]], [[sources/se-runbook-third-party]]
- Updated: [[modules/third-party]] (appended [[sources/se-runbook-third-party]] to source:; added ## Related Runbooks section before ## Open Questions — no other prose changed; last_updated preserved 2022-03-10), [[index]] (counts 147→149, Runbooks 28→29, Sources 51→52)
- Sources: 1 doc — WorkInSync Slack Integration (v1.0, 2022-03-10), the docx variant of the same doc the module already sources as a PDF ([[sources/wis-slack-integration]]). Same content; no new facts. Added the missing operational install runbook + homed the crawl docx.
- Secrets redacted: none (no Slack tokens / JWTs / client_secret in source).
- Flags: carried forward — ⚠️ 4-way data-storage contradiction in the 2022 doc (do not cite for compliance); unnamed backing modules for booking/check-in; missing Slack OAuth scope names; 2022 source freshness. No new evidence resolves these.

## [2026-06-29 22:05] ingest | SE Runbook — Employee Experience topic (Phase D) — closes module phase
- Created: [[runbooks/configurable-sender-email-setup]], [[sources/se-runbook-employee-experience]]
- Updated: [[modules/employee-experience]] (added configurable-sender-email capability to Known Features + Related Runbooks section; appended source; partially resolved Open Question #1; last_updated preserved 2024-02-27), [[index]] (counts 149→151, Runbooks 29→30, Sources 52→53)
- Source: 1 doc — PB-22330 Configurable sender email (emp-exp API + TC_1..TC_4 sender-resolution precedence). Service: EMAIL-EMP-EXPERIENCE.
- Secrets redacted: 1 HS512 x-wis-token JWT → <HS512 JWT — redacted>. Sender addresses (noreply@workinsync.io / transport@moveinsync.com) kept — documented system addresses, not credentials.
- Flags: PB-22330 note undated — confirm current behavior. ⚠️ Module phase of Phase D now COMPLETE (all clean-active + merge-review + stub modules ingested). Remaining: 65 release-notes history layer + graph-consistency/recency sweep.

## [2026-06-29 22:40] graph-sweep | Phase D bidirectional-link & recency consistency pass
- Tooling: /tmp/graph_sweep.py parses all 25 module frontmatter depends_on/used_by → flags asymmetries. Before: 7 asymmetries. After: 0.
- ETS reciprocity (added `ets` to depends_on + body Dependencies, tagged _(setup-time)_): [[modules/desk-management]], [[modules/guard-app-kiosks]], [[modules/parking-management]], [[modules/meal-management]], [[modules/floor-kiosk]] (floor-kiosk: added a new ## Dependencies section). Updated [[modules/ets]] deferred-sweep note → resolved.
- Sanitization reciprocity (added `sanitization` to used_by + body Used By): [[modules/desk-management]], [[modules/guard-app-kiosks]].
- Entity reciprocity: [[entities/room-tag]] used_by += desk-management, parking-management (+ body Used By lines; bumped last_updated; added se-runbook-tags-desk-parking source).
- Recency resolution: [[modules/sso]] Integration Surfaces username line → "Email ID or Employee ID" (2024 Complete Guide supersedes 2023 Azure doc); resolved the ⚠️ open-question note.
- Declined edges (per §10 Rule 6 — no invented dependencies): `BOOKING-RULE-ENGINE` (config-only, no module page) on [[modules/guard-app-kiosks]] — documented as cross-cutting, not a depends_on; digital-wayfinding↔employee-experience (Drive filing only, not architectural) — converted to a non-edge traceability note on [[modules/employee-experience]].
- Verification: re-ran graph_sweep.py → 0 asymmetries; all new wikilink targets confirmed present. No new pages (counts unchanged: 151/30/53).
- Still open (content/freshness, NOT graph edges — deferred): ETS setup-vs-runtime dependency nature; ms-teams→desk/emp-exp soft surfacing (no confirmed dependency); personalGuest dynamic-field schema gap; Outlook-2021 + PB-22330 freshness; several `.com`-only configs.

## [2026-06-29 18:30] ingest | Release Notes 2026 — RN 01-2026 through RN 05-2026 (Phase D history layer)
- Created: [[history/release-notes-2026]], [[history/release-notes]]
- Updated: [[index]] (total 151→153, added Release Notes: 2 counter, new ## Release Notes (History) section)
- Sources: 5 × raw .pptx files (RN 01–05-2026) via /tmp/rn2026_inputs.md — no per-RN source-summary pages created in this batch; raw_paths cited inline in the year page.
- Features ingested: 33 total across visitor-management (9), meeting-rooms (12), parking-management (3), meal-management (2), employee-experience (2), floor-kiosk (3), safe-reach (2), access-management (1), desk-management (3).
- ⚠️ Flags:
  - RN 01-2026 `enableOtpOverride`: consistent with existing [[modules/visitor-management]] curation. New companion property `failureReasonsOtp` not previously documented — noted inline; no wiki page rewrite needed.
  - RN 01-2026 Safe Reach report (PB-61094) and DigiPass auto-send (PB-61094) share the same PB number in source — source text artifact; both features distinct.
  - RN 05-2026 Room Name Filter (slide 16–17) and RN 01-2026 RFID column fix (slide 16–17): source deck text truncated at "ana…" / "inco…" — enablement/PB not extractable; raw .pptx linked in Linked Raw Evidence table.
  - RN 05-2026 NDA Scroll-Gated (DPDPA): appears in RN 04-2026 source deck (slide 18–19, after PB-64462), not RN 05 — placed under RN 04-2026 entry accordingly.
- Token scan: CLEAN — no JWTs, bearer tokens, email addresses, or secrets in output.

## [2026-06-30 00:00] ingest | Release Notes 2025 — RN 01-2025 through RN 15-2025 (Phase D history layer, batch 2)
- Created: [[history/release-notes-2025]]
- Updated: [[index]] (total 153→154, Release Notes counter 2→3, added row for release-notes-2025), [[history/release-notes]] (2025 row marked Done with link; 2025 Feature→Module Quick Map section added)
- Sources: 14 raw .pptx files (RN 01–08-2025, RN 09&10-2025 combined, RN 11–15-2025) via /tmp/rn2025_inputs.md — no per-RN source-summary pages created; raw_paths cited inline in the year page.
- Features ingested: 58 total across desk-management (22), meeting-rooms (7), parking-management (8), meal-management (7), employee-experience (7), visitor-management (5), access-management (5), delegation (2), floor-kiosk (4), tags-desk-parking (1), ets (3), employee-provisioning (1).
- ⚠️ Flags:
  - RN 01-2025 Hierarchy Search (PB-48836) + RN 02-2025 further refinement: two-step ship; RN 02 is the fuller implementation (limit 100, sorted by hierarchy level).
  - RN 02-2025 Partial Desk Search: initial ship; refined in RN 05-2025 (PB-52060) with admin-page coverage.
  - RN 05-2025 `allowOfficeCheckInWithoutDesk`: enabling property shared with RN 06-2025 individual resource check-out (PB-54141) — two distinct features on one property; flagged inline.
  - RN 06-2025 OTP Validation VMS (`kioskRequireOTPBeforeRegister`): superseded/enhanced by RN 01-2026 (`enableOtpOverride`, `failureReasonsOtp`) — flagged with ⚠️ inline.
  - RN 07-2025 + RN 08-2025 Chargeback Holiday-Aware (PB-53019): same PB in both decks; RN 07 treated as the ship date; RN 08 reference flagged as a duplicate.
  - RN 07-2025 Enhanced Resource Release (PB-51044): also in RN 06-2025; RN 06 is the earlier ship; RN 07 reference noted as duplicate.
  - RN 12-2025 Outlook Add-In Native Rooms (PB-59218): enhanced in RN 02-2026 (PB-62938) — flagged with ⚠️ inline.
  - RN 15-2025 Admin Dashboard 2.0 Cross-Office: further fixes in RN 03-2026 (PB-63436) — flagged with ⚠️ inline.
  - Several slides in source decks were truncated mid-text (`...[truncated]`) — where PB or enablement was cut, noted as "(see raw evidence)" rather than guessing.
  - RN 02-2025 body text was sparse in extracted content; features reconstructed from available slide text + pattern matching; raw .pptx is the authoritative source.
- Token scan: CLEAN — no JWTs, bearer tokens, email addresses (`*@moveinsync.com`/`*@workinsync.io`), `Basic <base64>`, or `client_secret` values in output.
