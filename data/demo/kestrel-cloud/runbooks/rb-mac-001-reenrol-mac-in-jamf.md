---
id: RB-MAC-001
title: Re-enrol a Mac that dropped out of Jamf
doc_type: runbook
system: jamf
owner: Endpoint Engineering
access: it-staff
updated: 2026-09-14
tags: [macos, mdm, enrolment, jamf, ade]
---

# Re-enrol a Mac that dropped out of Jamf

## Purpose

Restore MDM management for a Kestrel Mac that has stopped checking in to Jamf Pro
(`https://jamf.kestrelcloud.example`), shows **"MDM profile is not installed"** in the inventory record, or no longer
receives configuration profiles and Self Service policies.

## Scope

All company-owned Macs enrolled through Automated Device Enrollment (ADE). Personal Macs are out of scope. If the Mac
was never enrolled (new joiner device), use RB-GEN-001 instead.

## Prerequisites

- Jamf Pro role **Endpoint Admin** or **Service Desk L2**.
- The serial number is assigned to the Kestrel MDM server in Apple Business Manager (ABM) and scoped to the
  `Kestrel-ADE-Standard` PreStage enrolment.
- The user can be on a call with you and has admin rights for the session (request temporary admin through Self
  Service > "Make Me Admin (30 min)" if the framework still works; otherwise use the LAPS account from the inventory
  record).

## Symptoms people report

- Self Service is empty or will not open; Wi-Fi `Kestrel-Corp` stops connecting after certificate expiry (KB-0006).
- MeshGate fails posture with `MG-301 device not managed` (RB-NET-001).
- Jamf inventory: "Last Check-in" older than 14 days, "MDM Profile Expiration" in the past, or the
  "MDM capable: No" flag.

## Steps

1. Check the current state on the Mac:
   ```bash
   sudo profiles status -type enrollment
   sudo profiles show -type enrollment
   sudo jamf checkJSSConnection
   ```
   Healthy output is `Enrolled via DEP: Yes` and `MDM enrollment: Yes (User Approved)`.
2. If the framework is intact but the MDM profile is missing, re-trigger ADE enrolment:
   ```bash
   sudo profiles renew -type enrollment
   ```
   The user gets a "Device Enrollment" notification. They must click it and approve the profile in
   **System Settings > General > Device Management**. Approval cannot be done remotely.
3. If `checkJSSConnection` fails or the `jamf` binary is missing, remove the stale framework first:
   ```bash
   sudo jamf removeFramework
   sudo profiles renew -type enrollment
   ```
4. If `profiles renew` returns `Error fetching Device Enrollment configuration` the serial is not assigned in ABM or
   the PreStage scope is wrong. In ABM, confirm the device is assigned to "Kestrel Jamf Pro", then in Jamf open
   **Computers > PreStage Enrollments > Kestrel-ADE-Standard > Scope** and add the serial. Wait 5 minutes and repeat
   step 2.
5. After enrolment, force inventory and policy:
   ```bash
   sudo jamf recon
   sudo jamf policy
   ```
6. Confirm the bootstrap token is escrowed (needed for software updates and FileVault):
   ```bash
   sudo profiles status -type bootstraptoken
   ```
   If it reports `escrowed to server: NO`, run `sudo profiles install -type bootstraptoken` with the user's
   credentials.

## Verification

- Jamf record shows a fresh check-in, "MDM capable: Yes" and "User Approved MDM: Yes".
- Configuration Profiles tab lists `KC-Baseline-Security`, `KC-WiFi-Corp-EAPTLS` and `KC-FileVault-Escrow`.
- FileVault recovery key is valid; if not, follow RB-MAC-002.

## Rollback

Re-enrolment is non-destructive. If enrolment loops, leave the device as-is and do not wipe; capture
`sudo log show --predicate 'subsystem == "com.apple.ManagedClient"' --last 1h > ~/Desktop/mdm.log` and escalate.

## Escalation

Endpoint Engineering via HELP ticket component "Jamf". For more than 10 Macs affected at once (APNs certificate or
ADE token expiry), raise a SEV2 per CF-005 and page Endpoint Engineering on-call.
