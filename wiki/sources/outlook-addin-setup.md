---
type: source
raw_path: raw/modules/meeting-rooms/Copy of Meeting Rooms_Setting up Outlook Add-in for Outlook Integration.docx
ingested: 2026-04-27
doc_type: spec
---

# Setting up Outlook Add-in for Outlook Integration

## Source Title
Setting up Outlook Add-in

## Date
Unknown

## Type
spec (setup guide)

## Key Takeaways
- WorkInSync Outlook Add-in is **not on the Microsoft App Marketplace** — installed via manifest XML URL.
- **Two deployment methods**:
  1. Individual install: Outlook → Get Add-ins → My Add-ins → Custom Add-ins → Add from URL → paste manifest URL.
  2. Org-wide deployment: Microsoft 365 Admin Center → Settings → Integrated Apps → Upload Custom Apps → provide manifest link, set user/group scope.
- Deployment can take up to 6 hours to propagate; Outlook restart may be required.
- `Specific users/groups` deployment scope does not include nested group members — Microsoft 365 limitation.
- The WIS team provides the manifest URL to clients.

## Entities Mentioned
- None

## Modules Mentioned
- [[modules/meeting-rooms]] (primary)
- [[modules/ms-teams-integration]] (Outlook/Microsoft ecosystem)

## Decisions Extracted
- None.

## Wiki Pages Created/Updated
- Updated: [[modules/meeting-rooms]]

_Source: [[sources/outlook-addin-setup]]_
