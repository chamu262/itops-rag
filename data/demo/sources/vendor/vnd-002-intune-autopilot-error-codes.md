---
id: VND-002
title: Microsoft Intune - Windows Autopilot error code reference
doc_type: vendor
system: intune
owner: Endpoint Engineering
access: it-staff
updated: 2026-07-03
tags: [intune, autopilot, windows, error-codes, esp, enrolment]
---

# Microsoft Intune - Windows Autopilot error code reference

Kestrel IT's working notes on Autopilot errors we see in user-driven, Entra-joined deployments. Procedure: RB-WIN-001.
Codes are HRESULTs shown on the OOBE error page or in the ESP "View details" pane.

## Where to look

- On the device: Shift+F10, then `mdmdiagnosticstool.exe -area Autopilot;DeviceEnrollment;DeviceProvisioning -cab
  C:\Temp\ap.cab`.
- Event Viewer: `Applications and Services Logs > Microsoft > Windows > ModernDeployment-Diagnostics-Provider >
  Autopilot` and `DeviceManagement-Enterprise-Diagnostics-Provider > Admin`.
- Intune: **Devices > Monitor > Autopilot deployments** (shows phase and failing app).
- PowerShell community script `Get-AutopilotDiagnostics` reads the same data offline.

## Enrolment and join errors

These appear before or during MDM enrolment, usually right after the user signs in on the OOBE screen.

## 0x80180014

MDM enrolment blocked. In our tenant: the device was deleted from Intune while its Autopilot record remained (Intune
marks it blocked), or Windows enrolment restrictions block personally owned devices and the device is not recognised as
corporate. Fix: **Unblock device** in Windows enrolment devices; confirm the Autopilot record exists.

## 0x80180018

User has no licence that includes Intune. Add to the licensing group and wait for assignment.

## 0x8018002b

MDM user scope or UPN issue: user not in the MDM user scope group, or UPN suffix not verified. Kestrel's MDM user scope
is `SG-Intune-Autopilot-Users`.

## 0x801c03ed

"Admin has blocked this device" or device not allowed to join. Usually a disabled or duplicate Entra device object,
or the Autopilot device object was deleted from Entra. Remove stale device objects (not the Autopilot one).

## 0x801c0003

User not allowed to join devices to Entra (Device settings > "Users may join devices"). Kestrel allows the Autopilot
users group only.

## 0x80180005 / 0x80070002 at enrolment

Generic server or network errors; check proxy and that `enterpriseregistration.windows.net` and
`enrollment.manage.microsoft.com` are reachable.

## Enrollment Status Page (ESP) errors

These appear after enrolment, while the ESP tracks policies and apps in the device and account setup phases.

## 0x800705b4

Timeout. ESP default at Kestrel is 60 minutes. Almost always a large or failing blocking app. Reduce the blocking
list rather than raise the timeout.

## 0x81036502

An app failed to install during ESP. Check which app in Intune; for Win32 apps check the IME log
`C:\ProgramData\Microsoft\IntuneManagementExtension\Logs\IntuneManagementExtension.log`.

## 0x87D1041C

App detection rule did not detect the app after install (Win32). The installer succeeded but the detection rule is
wrong; fix the rule.

## 0x81036501

Error in device setup phase applying policies, often a conflicting configuration profile or a certificate profile
(SCEP) failing. Check the Wi-Fi certificate profile assignment.

## Other phases

Less common at Kestrel, listed so search finds them.

## 0x800705b4 in "Securing your hardware" (TPM attestation)

Pre-provisioning or self-deploying modes only; not used at Kestrel.

## "Something went wrong" with no code after reboot

Usually network loss during the device setup phase. Reboot and retry on wired network.

## Kestrel conventions

- Group tag `KC-STD` for standard laptops, `KC-DEV` for developer builds (local admin via LAPS only).
- Autopilot profile name template `KCW-%SERIAL%` (Autopilot only supports `%SERIAL%` and `%RAND:x%`); a remediation
  script renames the device to `KC-<SITE>-WL-<asset>` after enrolment (CF-003).
- ESP blocking apps: Company Portal, MeshGate, Defender onboarding, KC baseline config.
