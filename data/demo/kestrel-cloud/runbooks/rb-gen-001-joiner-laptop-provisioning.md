---
id: RB-GEN-001
title: Joiner laptop provisioning end-to-end
doc_type: runbook
system: general
owner: Service Desk
access: it-staff
updated: 2026-09-09
tags: [onboarding, joiner, provisioning, autopilot, ade, jamf, intune]
---

# Joiner laptop provisioning end-to-end

## Purpose

Deliver a ready-to-work laptop and accounts to a new starter on day one, with zero-touch enrolment so the device is
compliant before first sign-in.

## Scope

Permanent staff and contractors in all four offices (STO, LON, AUS, LIS) and remote hires. Standard hardware is a
MacBook Pro or a Windows 11 laptop depending on role profile.

## Prerequisites

- HR record created in the HR system at least 10 working days before start; this triggers account creation in Entra
  via the HR inbound provisioning job (runs hourly).
- HELP ticket of type "New starter" with role profile, office and hardware choice.
- Device purchased through the reseller with Apple Business Manager or Autopilot registration (reseller uploads the
  hardware hash).

## Steps

1. **T-10 days: account.** Confirm the Entra user exists (`Get-MgUser -UserId first.last@kestrelcloud.example`),
   `accountEnabled` is false until start date, and dynamic groups from department and office have populated
   (`SG-Office-STO`, `SG-Dept-Engineering`, etc.). Google Workspace account is provisioned from Entra via SCIM.
2. **T-7: device assignment.**
   - Mac: confirm the serial is in ABM, assigned to "Kestrel Jamf Pro", and scoped to PreStage
     `Kestrel-ADE-Standard`. Set the asset tag and name per CF-003 (`KC-STO-MBP-04217`).
   - Windows: confirm the Autopilot record has group tag `KC-STD`, deployment profile **Assigned**, and set the
     assigned user so the sign-in screen is pre-filled.
3. **T-5: test enrolment.** Endpoint Engineering does not pre-stage Macs by default; for executive and remote hires,
   Service Desk runs enrolment once on the bench to pull apps, then erases (Mac: Erase All Content and Settings;
   Windows: Autopilot Reset).
4. **T-3: ship or stage.** Remote: ship with tracking, recorded on the ticket. Office: place in the locker for the
   start date.
5. **Day 1, 09:00 local.** HR provisioning enables the account. Service Desk issues a Temporary Access Pass valid
   8 hours (see RB-IDM-001 step 5) and gives it to the joiner on the welcome call after identity check.
6. **Day 1 enrolment.**
   - Mac: power on, join Wi-Fi (`Kestrel-Guest` in the office, home Wi-Fi remote), ADE enrolment, Platform SSO
     registration with the TAP, then password set. Baseline apps install via Jamf (about 25 min).
   - Windows: Autopilot OOBE, sign in with the TAP, ESP installs blocking apps. Failures: RB-WIN-001.
7. **Day 1 security info.** Joiner registers Authenticator (KB-0001) and sets a password (KB-0003). TAP expires.
8. **Day 1 check.** Joiner connects MeshGate (KB-0002), opens Gmail and Drive, joins Wi-Fi `Kestrel-Corp` (KB-0006).

## Verification

- Jamf or Intune shows the device compliant with correct primary user.
- FileVault/BitLocker key escrowed (RB-MAC-002, RB-WIN-003).
- Ticket checklist ticked: device, MFA, MeshGate, GWS, app access requested in Self Service / Company Portal (KB-0004).

## Rollback

If the start date moves, HR updates the record; the account stays disabled. Hardware stays assigned. If the hire is
cancelled, run the leaver checklist RB-GEN-002 (shortened: no data transfer).

## Escalation

Service Desk owns. Enrolment issues: Endpoint Engineering. Account or group issues: Identity & Access. Joiner
without a working laptop by 11:00 on day one is a P2 ticket (KB-0014).
