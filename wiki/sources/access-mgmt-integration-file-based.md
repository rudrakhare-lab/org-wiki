---
type: source
raw_path: raw/modules/access-management/WorkInSync Access Card Management Integration - File based [Client shareable].pdf
ingested: 2026-05-27
doc_type: spec
---

# Access Card Management Integration — File based (SFTP)

## Source Title
WorkInSync Access Card Management Integration - File based

## Date
Feb 10, 2025 (v1.0, "Initial Doc"). Author: Aditya Dutta / approved Ujjwal Trivedi. Classification: **Confidential**. This is the newest of the access-management source docs — the file-based mode was added ~7 months after the API-based v1.2.

## Type
spec

## Key Takeaways
- **Alternative integration mode to the API.** Source quote (Purpose): *"This document explains the process and data required for integrating the WorkInSync system with client's own/third party access management vendors using a transfer of CSV files via a SFTP server."* Instead of real-time REST calls, clients push CSV swipe-data files to an SFTP server on a configured frequency.
- **Value props ("What WorkInSync solves")**: visibility into employee check-in/out adherence; employee-centric card-swipe check-in; resource-utilization reports; **anomaly highlighting** (a report of users who entered the office without a booking); optional config to reject entry of users without a booking; optional config to auto-create a booking and check them in.
- **Prerequisites**: SSH (Secure Shell) key; IP addresses to whitelist; encryption used during transfer (if any); file frequency (e.g. 1 hour, after SFTP config is done).
- **Operating procedure** (5 steps): client provides prerequisites → WorkInSync configures and shares port/filepath/server → connection tested → WorkInSync shares file format with the customer → customer pushes a sample file.
- **⚠️ Source is INCOMPLETE.** Page 3 has a "File format" heading with NO body content, and a "Report insights" heading with NO body content. The actual CSV schema and the report contents are **absent from this source**. A consumer cannot determine the required CSV fields from this doc alone — a separate/updated source is needed.

## Entities Mentioned
(none)

## Modules Mentioned
- [[modules/access-management]] (primary subject)

## Decisions Extracted
(none)

## Wiki Pages Created/Updated
- Created: [[modules/access-management]]
- Updated: [[index]], [[log]]

_Source: [[sources/access-mgmt-integration-file-based]]_
