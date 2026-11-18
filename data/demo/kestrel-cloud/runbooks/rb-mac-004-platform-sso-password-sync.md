---
id: RB-MAC-004
title: Platform SSO or Jamf Connect password out of sync
doc_type: runbook
system: jamf
owner: Endpoint Engineering
access: it-staff
updated: 2026-10-08
tags: [macos, platform-sso, jamf-connect, entra, password]
---

# Platform SSO or Jamf Connect password out of sync

## Purpose

Fix Macs where the local login password no longer matches the user's Entra ID password. Kestrel is migrating from
Jamf Connect to macOS Platform SSO (Microsoft Enterprise SSO plug-in, delivered by Company Portal) during 2026; both
appear in the estate.

## Scope

Jamf-managed Macs. Check which method the Mac uses in Jamf inventory extension attribute **"Login Sync Method"**
(`PlatformSSO` or `JamfConnect`).

## Symptoms

- Platform SSO: notification "Registration Required" or "Sign in required. Your Microsoft Entra password was
  changed", repeated keychain prompts, `AADSTS50173` (grant expired after password change) in Company Portal logs.
- Jamf Connect: menu bar shows "Your network password and local password are not in sync".
- The user changed their password on the web via SSPR (KB-0003) while the Mac was offline.

## Prerequisites

- User is online (office network or MeshGate) and knows both old local and new Entra password. If they do not
  know the old local password, see step 6.

## Steps: Platform SSO

1. Check registration state:
   ```bash
   app-sso platform -s
   ```
   Look for `Device Configuration` with `registrationCompleted: true` and the user's `loginType: Password`.
2. Ask the user to click the "Sign in required" notification and enter the **new** Entra password. Platform SSO
   updates the local account password and unlocks the keychain if the old one is supplied when prompted.
3. If registration itself is broken (`registrationCompleted: false`), have the user open **System Settings > Users &
   Groups > Network Account Server > Repair**, or re-run registration from the notification. Company Portal must be
   current (Self Service > "Company Portal").
4. Confirm token issuance with `app-sso platform -s | grep -i tokens`.

## Steps: Jamf Connect

5. Click the Jamf Connect menu bar icon > **Sign In**, authenticate with the new Entra password, then enter the old
   local password when prompted to sync.

## Both: user forgot old local password

6. Reset the local password with the LAPS admin from the Jamf record, then delete the stale login keychain only
   after the user confirms nothing important is stored there:
   ```bash
   sudo sysadminctl -resetPasswordFor <user> -newPassword - -adminUser kcadmin -adminPassword -
   ```
   FileVault PRK must then be rotated (RB-MAC-002) because the user's secure token password changed outside the normal
   flow.

## Verification

- User logs in at the FileVault screen with the new Entra password.
- `app-sso platform -s` shows a fresh `lastLoginDate` and SSO works in Safari to `myapps.microsoft.com`.

## Rollback

None needed. If a Mac must leave Platform SSO, remove it from smart group `PSSO - Enabled`; the Jamf Connect
profile re-applies through `SG-Mac-JamfConnect-Legacy`.

## Escalation

Endpoint Engineering for registration failures; Identity & Access if Entra sign-in logs show the device as not
compliant or blocked by Conditional Access (RB-IDM-002).
