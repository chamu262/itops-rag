---
id: RB-SEC-001
title: Lost or stolen device (remote lock and wipe)
doc_type: runbook
system: security
owner: Security Operations
access: it-staff
updated: 2026-07-15
tags: [security, lost-device, stolen, remote-wipe, jamf, intune, incident]
---

# Lost or stolen device

## Purpose

Contain the risk from a lost or stolen company laptop or phone: cut access, lock or wipe, and record the event.

## Scope

Company Macs (Jamf), Windows laptops (Intune), company iPhones (Jamf) and the managed apps on personal phones
(Intune App Protection).

## Prerequisites

- Jamf and Intune admin rights for lock/wipe (Service Desk L2, Endpoint Engineering).
- HELP ticket with device name or serial, time and place of loss, and whether a police report exists (stolen).

## Steps

1. **Open a security ticket.** Create the HELP ticket with component "Lost/Stolen" and add Security Operations as
   watcher. Theft or loss with sensitive data access (Finance, Legal, Admin roles) is SEV3 minimum.
2. **Revoke sessions** so the device's tokens stop working:
   ```powershell
   Revoke-MgUserSignInSession -UserId user@kestrelcloud.example
   ```
   And in Google: `gam user user@kestrelcloud.example signout`.
3. **MeshGate**: revoke the specific device in the admin console (**Users > Devices > Revoke**).
4. **Lock the device.**
   - Mac (Jamf): computer record > **Management > Lock Computer**, set a 6-digit PIN and a message: "This device
     belongs to Kestrel Cloud. Call +46 8 555 010 00." Record the PIN in the ticket (restricted field).
   - iPhone (Jamf): enable **Lost Mode** with the same message; this also reports location when the device is online.
   - Windows (Intune): device > **Remote lock**. Confirm BitLocker is on (RB-WIN-003 for the key ID).
5. **Decide on wipe.** Wipe immediately if the device is stolen, if FileVault/BitLocker status is unknown, or after
   7 days if still lost. Otherwise wait so the device can be recovered intact.
   - Mac: **Wipe Computer** (Erase All Content and Settings on Apple silicon).
   - iPhone: **Wipe Device**; keep the Activation Lock bypass code escrowed in Jamf.
   - Windows: **Wipe**, untick "retain enrolment state".
   - Personal phone: **App selective wipe** only; never full wipe a personal device.
6. **Credentials.** User resets their password (KB-0003). If the phone held Authenticator, follow RB-IDM-001 to
   remove it and register a new device.
7. **Replacement.** Issue a loaner from stock and provision as a joiner device (RB-GEN-001 steps 2 and 6).
8. **Record.** Update the CMDB asset as Lost or Stolen; attach the police reference if supplied.

## Verification

- Jamf/Intune show the command as Acknowledged or Pending (pending is acceptable; it executes when online).
- Entra sign-in logs show no successful sign-ins from the device ID after the revoke time.

## Rollback

If the device is found before wipe: user unlocks with the PIN supplied by Service Desk after identity check, disable
Lost Mode, re-register MeshGate device.

## Escalation

Security Operations decides on wider response, for example if the device was taken with an unlocked session or in a
targeted theft. Data-protection reporting is decided by Security Operations and Legal, not Service Desk.
