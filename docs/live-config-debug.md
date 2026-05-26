# Live Config Debug Playbook

Use this whenever a user reports a bug that might be caused by a PMS config value.
The static wiki documents ~1800 *default* config values. This workflow fetches the
*actual values set for a specific customer* at each level of the hierarchy.

---

## Conceptual model

Every PMS property has a **resolution chain**. The most specific level that has an
override wins:

```
DEFAULT  (system default from /default-properties/details)
  └─▶  BUID override   (applies to all offices under this BUID)
         └─▶  OFFICEID override  (applies to one office)
                └─▶  ROOMID override   (meeting-rooms only — applies to one room)
                     └─▶  ROLE override    (PMS service only — applies to one role)
```

A value set at OFFICEID level will override BUID level **only for that office**.
The BUID-level value still applies to all other offices. Same rule for ROOMID over
OFFICEID, and ROLE over OFFICEID.

The `criteriaPriorityList` on each property's metadata tells you the exact override
order for that property. Priority 1 = most specific (wins).

---

## Session storage

Sessions are cached in `/tmp/pms_debug_<SERVICE>_<BUID>.json`. They are never
committed to the repo — they contain customer config data.

A session stores:
- All default property metadata (from `default-properties/details`)
- Configs fetched at each level (BUID, specific offices, rooms, roles)
- Criteria values (list of OFFICEIDs, ROOMIDs, etc.)

Sessions persist until you delete them or the `/tmp/` directory is cleared.

---

## Step 1 — Gather context before fetching anything

**Do not start fetching until you know:**

| Question | Why it matters |
|----------|---------------|
| Which **service**? | The API and properties differ by service |
| Which **BUID**? | All fetches are scoped to one BUID |
| Which **level** is the bug at? | Determines which API body to send |
| Which **OFFICEID / ROOMID / ROLE**? | Required for non-BUID level fetches |

**Ask explicitly:** "Is this bug affecting all offices under this BUID, or a specific
office? If specific, what is the OFFICEID?"

**Do not guess** the level. The same property can show different values at BUID vs.
OFFICEID level. Only the user knows which office/room/role is exhibiting the bug.

---

## Step 2 — Map bug to service ID

| Wiki module | Service ID for API |
|-------------|-------------------|
| `visitor-management` | `VISITOR` |
| `meeting-rooms` | `MEETING_ROOMS` |
| `booking-rule-engine` | `BOOKING-RULE-ENGINE` |
| `desk-management` | `WIS-SEAT-BOOKING` |
| `guard-app-kiosks` | `GUARD-APP` |
| `employee-experience` (email) | `EMAIL-EMP-EXPERIENCE` |
| `employee-experience` (internal) | `EMP-EXP-INTERNAL-CONFIG` |
| `employee-experience` (common) | `EMP-EXP-COMMON-CONFIG` |
| `pms` (role-level) | `PROJECT-MANAGEMENT-SERVICE` |

**Known ROLE values for `PROJECT-MANAGEMENT-SERVICE`:**
- `employee`
- `RECEPTIONIST`
- `cd210644-153b-4a57-aa48-5e7213a5da66` (admin/super-admin UUID)

---

## Step 3 — Identify the server and initialize a debug session

WorkInSync runs two production server environments. Ask the user which server
their client is on before fetching anything:

| Server | Clients | Flag |
|--------|---------|------|
| `.com` (global) | International / default | `--server com` (default, can omit) |
| `.in` (India region) | India-region clients | `--server in` |

Sessions are stored separately per server — you can have simultaneous sessions for
both servers with no collision:
- `.com` → `/tmp/pms_debug_com_{SERVICE}_{BUID}.json`
- `.in`  → `/tmp/pms_debug_in_{SERVICE}_{BUID}.json`

Bearer tokens and cookies are **server-specific** — a `.com` token will not work on
`.in` and vice versa. Export server-specific vars once per shell session so you can
switch between servers without re-exporting:

```bash
# Recommended: server-specific vars (export both upfront)
export PMS_TOKEN_COM="eyJhbGci..."    # .com bearer token
export PMS_TOKEN_IN="eyJhbGci..."     # .in  bearer token
export PMS_COOKIE_COM="JSESSION=..."  # .com cookie (optional)
export PMS_COOKIE_IN="JSESSION=..."   # .in  cookie (optional)

# Fallback: single PMS_TOKEN used for both servers if _COM/_IN vars are not set
export PMS_TOKEN="eyJhbGci..."
```

The script automatically picks `PMS_TOKEN_COM` for `--server com` and `PMS_TOKEN_IN`
for `--server in`. If the server-specific var is missing, it falls back to `PMS_TOKEN`.

Initialize session and load property metadata:

```bash
# .com server (default — omit --server for .com clients)
python scripts/pms_debug.py --service VISITOR --buid genpactindia-GInd init

# .in server (India-region clients)
python scripts/pms_debug.py --server in --service VISITOR --buid someIndiaBuid init
```

This calls `/{SERVICE}/default-properties/details` on the appropriate server and
caches the full property list with metadata (data type, definition, criteriaPriorityList).

---

## Step 4 — Fetch configs at the relevant levels

All commands below work identically for both servers — just add `--server in` for
India-region clients. Examples below show `.com`; substitute `--server in` as needed.

### Always fetch BUID level first (baseline)

```bash
python scripts/pms_debug.py --service VISITOR --buid genpactindia-GInd fetch
# .in server:
python scripts/pms_debug.py --server in --service VISITOR --buid <buid> fetch
```

### If the bug is office-specific — map names, then fetch office level

```bash
# Step 1: load the OFFICEID → office name mapping (run once; cached in session)
python scripts/pms_debug.py --service VISITOR --buid genpactindia-GInd list-offices
# Output example:
#   Found 5 offices:
#     WorkInSync Pune (Pune, India)
#       OFFICEID: LOwfoMIS-$000-0000-0000-000000096334
#     WorkInSync (Bangalore, India)
#       OFFICEID: LOwfoMIS-$000-0000-0000-000000001332

# Step 2: list OFFICEIDs that actually have config overrides set
python scripts/pms_debug.py --service VISITOR --buid genpactindia-GInd \
    list-criteria OFFICEID

# Step 3: fetch configs for the specific office:
python scripts/pms_debug.py --service VISITOR --buid genpactindia-GInd \
    fetch --criteria OFFICEID --value LOwfoMIS-$000-0000-0000-000000096334
```

Once `list-offices` has run, all subsequent `diagnose`, `compare`, and `report`
outputs automatically show the office name next to every OFFICEID — no further
lookups needed.

### For meeting-rooms room-specific bug

```bash
python scripts/pms_debug.py --service MEETING_ROOMS --buid <buid> \
    fetch --criteria ROOM_ID --value <roomid>
```

### For PMS role-specific bug

```bash
python scripts/pms_debug.py --service PROJECT-MANAGEMENT-SERVICE --buid <buid> \
    fetch --criteria ROLE --value employee
# or: --value RECEPTIONIST
# or: --value cd210644-153b-4a57-aa48-5e7213a5da66
```

---

## Step 5 — Compare and generate fix guidance

```bash
# Compare one property across all fetched levels:
python scripts/pms_debug.py --service VISITOR --buid genpactindia-GInd \
    compare --property checkinBufferFromKiosk

# Full report with fix guidance:
python scripts/pms_debug.py --service VISITOR --buid genpactindia-GInd \
    report --property checkinBufferFromKiosk
```

The report output shows:
- **DEFAULT** value (system default)
- **BUID** value (override for the whole BUID, if set)
- **OFFICEID::\<id\>** value (office override, if set)
- **Effective value** — which level is actually winning
- **Fix guidance** — which level to change and why

---

## Step 6 — Cross-reference wiki + Jira

After getting the live values, always combine with:

1. **Wiki config page:** `wiki/configs/<service-slug>.md` — documented behavior and notes
2. **Jira SQLite:** search for the property name in ticket descriptions/comments:
   ```bash
   sqlite3 raw/jira/tickets.sqlite "
     SELECT key, summary, substr(description_text,1,400)
     FROM tickets
     WHERE description_text LIKE '%checkinBufferFromKiosk%'
     LIMIT 5
   "
   ```
3. **Property definition:** the `propertyDefinition` field from default-properties

**Response pattern:**

> "The wiki documents `checkinBufferFromKiosk` as: *Defines buffer time (in minutes)
> for active booking check-in via kiosk* [[configs/visitor-management]].
>
> Live fetch for BUID `genpactindia-GInd`:
> - DEFAULT = 0
> - BUID level = 5
> - OFFICEID `LOwfoMIS-...` level = **10** ← **effective value**
>
> The bug is at OFFICEID level — this office has a 10-minute buffer which is
> overriding the BUID-level value of 5. To fix, update `checkinBufferFromKiosk`
> at OFFICEID level in CMS.
>
> Jira: SE-12345 shows a previous case where this config caused check-in timing issues."

---

## Common debugging patterns

### "Config changed at BUID level but offices aren't picking it up"

Fetch both BUID and OFFICEID levels. If an OFFICEID-level override exists,
it will always win — the BUID change has no effect on that office until the
OFFICEID override is removed or updated.

### "Feature is enabled globally but broken for one office"

Likely an OFFICEID-level override with the wrong value. Fetch that OFFICEID
level and compare against BUID level.

### "Config is correct in one BUID but wrong in another"

Session is per-BUID. Create a second session for the other BUID and compare.

### "Don't know which property is causing the bug"

1. Run `fetch` at the relevant level to get all overrides at that level
2. Scan the override list for suspicious values
3. Compare each candidate with the DEFAULT using `compare --property`

```bash
# See all overrides at OFFICEID level:
python scripts/pms_debug.py --service VISITOR --buid <buid> \
    fetch --criteria OFFICEID --value <officeid> --verbose
```

---

## Session management

```bash
# See what's in the current session:
python scripts/pms_debug.py --service VISITOR --buid genpactindia-GInd show-session
python scripts/pms_debug.py --server in --service VISITOR --buid <buid> show-session

# Clear the session (e.g. after token expiry or to start fresh):
python scripts/pms_debug.py --service VISITOR --buid genpactindia-GInd clear-session
python scripts/pms_debug.py --server in --service VISITOR --buid <buid> clear-session
```

Session files:
- `.com` → `/tmp/pms_debug_com_<SERVICE>_<safe_buid>.json`
- `.in`  → `/tmp/pms_debug_in_<SERVICE>_<safe_buid>.json`

Both can coexist in `/tmp/` — they never collide even for the same service+buid pair.

---

## What this workflow does NOT do

- **Does not write configs.** This is read-only debugging. To fix a config, use the CMS dashboard.
- **Does not map OFFICEID → office name.** That API mapping isn't configured yet. User must provide OFFICEIDs.
- **Does not exhaustively fetch all offices.** Fetch only the levels relevant to the bug.
- **Does not replace Jira search.** Always run Jira alongside this for context.
