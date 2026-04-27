---
type: entity
owned_by: meeting-rooms
used_by: [meeting-rooms, meal-management]
last_updated: 2026-04-27
source: "[[sources/meeting-rooms-catering-prd]]"
---

# Cafeteria

## Description
A cafeteria is a food-service premise mapped to one or more offices. It contains categories,
each of which contains menu items. A Cafeteria can serve both Meeting Rooms catering and
Employee Meal booking — the `available_for` field distinguishes scope.
Managed by admins on the Configurations page (Stratus only for UI management; ETS+WIS supported via API).

## Fields
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| id | UUID | Unique cafeteria identifier | Yes |
| name | string | Cafeteria name (alphanumeric + special chars) | Yes |
| capacity | integer | Physical seating capacity (used for meal management, not meeting rooms) | No |
| floor_id | UUID | FK → Floor | No |
| office_ids | UUID[] | Offices this cafeteria serves (multi-select) | Yes |
| available_for | enum[] | `MEETING_ROOMS`, `EMPLOYEE_MEALS`, or both | Yes |
| currency | string | ISO currency code (default INR; 108 currencies supported) | Yes |
| categories | Category[] | Ordered list of menu categories (configurable order) | Yes |

### Category (nested)
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique category ID |
| name | string | Category name (rename without losing items) |
| order | integer | Display order (not alphabetical) |
| items | CateringItem[] | Items in this category |

### CateringItem (nested)
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Item ID |
| name | string | Item name |
| price | decimal | Price in cafeteria currency |
| item_type | enum | `VEG`, `NON_VEG`, `VEGAN` |
| prep_time_hours | integer | Preparation time in hours |
| availability_start | time | Earliest time item is available |
| availability_end | time | Latest time item is available |
| description | string | Optional description |
| cut_off_minutes | integer | Minutes before meeting that item can no longer be ordered |

## Used By
- [[modules/meeting-rooms]] — catering booking and dashboard
- [[modules/meal-management]] — employee meal booking (shared cafeteria entity)

## Relationships to Other Entities
- [[entities/catering-order]] — each CateringOrder references one Cafeteria
- [[entities/room]] — Rooms are mapped to Cafeterias (many-to-many via office)

## Source of Truth
[[modules/meeting-rooms]] currently owns the Cafeteria entity definition (Configurations page, PMS service).

⚠️ **Potential conflict**: [[modules/meal-management]] also uses Cafeteria for employee meals. Ownership of the shared entity needs clarification once meal-management spec is ingested.

_Source: [[sources/meeting-rooms-catering-prd]]_
