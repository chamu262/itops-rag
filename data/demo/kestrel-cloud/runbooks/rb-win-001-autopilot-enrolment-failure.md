---
id: RB-WIN-001
title: Windows Autopilot enrolment failure
doc_type: runbook
system: intune
owner: Endpoint Engineering
access: it-staff
updated: 2026-07-03
tags: [windows, autopilot, intune, enrolment, esp]
---

# Windows Autopilot enrolment failure

## Purpose

Diagnose and fix a Windows laptop that fails Autopilot user-driven enrolment (Entra join, no hybrid) during OOBE or
the Enrollment Status Page (ESP). The full error code list is in VND-002.

## Scope

Company-owned Windows 11 devices registered in the Kestrel Autopilot tenant with the `KC-Autopilot-UserDriven`
deployment profile.

## Prerequisites

- Intune role **Endpoint Admin** or **Help Desk Operator (Autopilot)**.
- Device hardware hash is uploaded (Intune > Devices > Enrollment > Windows Autopilot devices) and the profile status
  is **Assigned**.
- User has an Intune licence (group `SG-Lic-M365-E3`) and is in `SG-Intune-Autopilot-Users`.

## Common errors

| Code | Meaning at Kestrel | Typical fix |
|---|---|---|
| `0x80180014` | Device blocked from MDM enrolment. Usually the device was deleted from Intune while the Autopilot record stayed, or a personal-device enrolment restriction matched. | Step 3 |
| `0x801c03ed` | Device not allowed to join Entra; stale or disabled Entra device object. | Step 4 |
| `0x80180018` | User has no Intune licence. | Add to `SG-Lic-M365-E3`, wait 15 min |
| `0x801c0003` | User not permitted to join devices to Entra. | Check "Users may join devices" scope |
| `0x800705b4` | ESP timeout (60 min), usually a large Win32 app. | Step 5 |
| `0x81036502` | ESP app install failure. | Step 5 |

## Steps

1. At the error screen press **Shift+F10** for a command prompt, or use "View details". Capture diagnostics:
   ```cmd
   mdmdiagnosticstool.exe -area Autopilot;DeviceEnrollment;DeviceProvisioning -cab C:\Temp\ap.cab
   ```
2. Confirm the device sees its profile:
   ```powershell
   Get-Content C:\Windows\ServiceState\wmansvc\AutopilotDDSZTDFile.json
   ```
   Missing file means no profile assigned; check the group tag `KC-STD` and dynamic group `SG-AP-Devices-STD`.
3. For `0x80180014`: in Intune open **Devices > Windows > Windows enrolment > Devices**, find the serial. If the
   record shows "Blocked" or the Intune object was deleted, choose **Unblock device**. Also check **Enrollment
   restrictions**: Kestrel blocks "Personally owned" Windows; the Autopilot record must exist for the device to count
   as corporate.
4. For `0x801c03ed`: delete the disabled Entra device object with the same name, keeping the Autopilot object
   (it is the "Autopilot device" type in Entra; do not delete that one). Graph:
   ```powershell
   Get-MgDevice -Filter "displayName eq 'KC-LON-WL-03311'" | Select Id,AccountEnabled,TrustType
   ```
5. For ESP failures: Intune > device > **Managed apps** to see which app failed. Kestrel's ESP blocks only on
   Company Portal, MeshGate client, Defender onboarding and the baseline config. Remove any other app from the
   blocking list on `ESP-KC-Default` rather than raising the timeout.
6. Reset and retry: Shift+F10 then `shutdown /r /t 0`, or from Intune issue **Autopilot Reset** if the device
   reached the desktop.

## Verification

```cmd
dsregcmd /status
```
`AzureAdJoined : YES`, `DeviceAuthStatus : SUCCESS`, and the device appears in Intune with the correct primary user
and name `KC-<SITE>-WL-<asset>` (CF-003).

## Rollback

None; a failed device can be wiped with **Fresh start** or reimaged from USB and retried.

## Escalation

Endpoint Engineering. More than five devices failing with the same code in a day: check OC-005 known issues and
raise a SEV3.
