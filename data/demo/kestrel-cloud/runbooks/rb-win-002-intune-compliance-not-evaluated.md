---
id: RB-WIN-002
title: Intune compliance "Not evaluated" or stuck in grace period
doc_type: runbook
system: intune
owner: Endpoint Engineering
access: it-staff
updated: 2026-10-14
tags: [windows, intune, compliance, conditional-access, grace-period]
---

# Intune compliance "Not evaluated" or stuck in grace period

## Purpose

Resolve Windows devices whose compliance state is **Not evaluated**, **In grace period** or **Not compliant** when the
user believes the device is fine. Non-compliant devices are blocked by Conditional Access policy
`CA-020-Require-Compliant-Device` (sign-in error `AADSTS53000`), and MeshGate refuses them with `MG-301`.

## Scope

Intune-managed Windows 11 devices. For Macs, compliance comes from Jamf device compliance; follow RB-MAC-001 first.

## Prerequisites

- Intune role **Endpoint Admin** or **Help Desk Operator**.
- Know the policy set: `CMP-Win-Baseline` checks BitLocker, Secure Boot, Defender real-time, firewall, minimum OS
  build and Defender machine risk score "Medium or lower". Grace period is 3 days for OS build, 0 days for
  encryption.

## Steps

1. In Intune open the device > **Device compliance**. Note which setting fails. "Not evaluated" on every setting
   usually means the device has not checked in since the policy was assigned, or the user is not the primary user.
2. Check the built-in policy **Default Device Compliance Policy**: settings "Is active" and "Has a compliance policy
   assigned". A device that has not checked in for 30 days becomes Not compliant automatically.
3. On the device force a sync: **Settings > Accounts > Access work or school > Info > Sync**, or:
   ```powershell
   Get-ScheduledTask | Where-Object {$_.TaskName -eq 'PushLaunch'} | Start-ScheduledTask
   ```
   Then in Company Portal: **Settings > Sync** and **Check access**.
4. Confirm Entra registration is healthy:
   ```cmd
   dsregcmd /status
   ```
   Need `AzureAdJoined : YES`, `AzureAdPrt : YES`. If `AzureAdPrt : NO`, the user must sign out and in; if
   `DeviceAuthStatus : FAILED. Device is either disabled or deleted`, the device must be re-enrolled
   (RB-WIN-001).
5. Fix the failing setting:
   - BitLocker: `manage-bde -status C:`; if off, run the Intune remediation "Enable BitLocker".
   - OS build: install the pending cumulative update (Windows Update for Business ring, CF-004).
   - Defender risk: hand to Security Operations; do not override.
6. Wait for re-evaluation (up to 8 hours for the scheduled check, or immediate after a successful sync).

## Granting temporary access

Do not exclude users from `CA-020`. If the user must work during a fix, Identity & Access may add the device to
`SG-CA-Compliance-Exception` for a maximum of 72 hours with a HELP ticket reference. Exceptions are reviewed daily.

## Verification

Intune shows **Compliant**; Entra sign-in logs for the user show `Device compliant: Yes`. User's message in KB-0010
disappears after closing and reopening the app.

## Rollback

Remove the device from `SG-CA-Compliance-Exception` when compliant.

## Escalation

Endpoint Engineering for policy issues; Identity & Access for Conditional Access; Security Operations for Defender
risk. If many devices flip to "Not evaluated" at once, it is likely a service-side issue: check the Microsoft 365
service health and OC-005, then raise SEV3.
