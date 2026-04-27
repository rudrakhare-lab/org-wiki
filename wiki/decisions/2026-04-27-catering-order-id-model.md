---
type: decision
module: meeting-rooms
date: 2026-04-27
status: active
---

# Decision: Meeting ID is stable across edits; Order IDs are minted fresh on cancel+recreate

## Context
When a meeting with catering is edited (e.g. time change, attendee list change, delivery slot
change), the system needs to decide which identifiers survive the edit and which do not. This
affects order tracking, notification delivery, and downstream integrations.

## Decision
- **Meeting ID** is **stable** across all booking edits — it is the primary tracking ID used by
  facility managers and ops dashboards.
- **Order IDs** are regenerated when an order is cancelled and recreated. They are stable while
  the order is in `Requested` / `Accepted` / `Delivered` state.
- When delivery time changes: items are preserved in cart; the system checks each item's availability
  at the new time and marks unavailable items (does not auto-remove them). User can then adjust.
- When room or date changes: all catering orders are cancelled and must be re-created.

## Alternatives Considered
- **Make Order ID stable too** — rejected because fulfilment systems downstream need a clean ID
  when an order changes substantially (same ID with different contents causes confusion).
- **Clear cart on delivery time change** — previous behaviour (before v2.3); changed because
  users complained of having to re-select all items when only adjusting delivery time.

## Trade-offs
- Multiple Order IDs for the same Meeting ID means the catering dashboard must group by Meeting ID
  to show a coherent view of a single meeting's food requirements.
- Items that are unavailable at the new delivery time remain in the cart as "marked unavailable"
  rather than being removed — requires user action to clean up before submission.

## Source
[[sources/meeting-rooms-catering-prd]]
