---
id: RB-GEN-002
title: Leaver offboarding checklist across Entra, GWS, Jamf and Intune
doc_type: runbook
system: general
owner: Service Desk
access: it-staff
updated: 2026-09-23
tags: [offboarding, leaver, entra, gws, jamf, intune, access-removal]
---

# Leaver offboarding checklist

## Purpose

Remove access completely and on time when someone leaves, while keeping their data available to the business.

## Scope

All leavers. Standard leavers are processed at 18:00 local time on the last working day. **Urgent** leavers (HR flags
"immediate") are processed within 30 minutes of the HR request, regardless of time.

## Prerequisites

- HELP ticket of type "Leaver" created by HR with last day, manager, urgency and any legal hold note.
- Roles: User Administrator (Entra), KC User Lifecycle Admin (Google), Jamf and Intune device admin.

## Steps

1. **Confirm the request** came from HR in the ticket (not by email or Slack from a manager alone).
2. **Block sign-in in Entra** and revoke tokens:
   ```powershell
   Update-MgUser -UserId leaver@kestrelcloud.example -AccountEnabled:$false
   Revoke-MgUserSignInSession -UserId leaver@kestrelcloud.example
   ```
   This stops new sign-ins to all federated apps including Google and MeshGate.
3. **Remove authentication methods** (Authenticator, phone, FIDO2) so the account cannot be re-enabled and used
   without IT. Keep the user object for 30 days.
4. **MeshGate**: in the admin console, **Users > (user) > Revoke all devices**. Existing tunnels drop within 60
   seconds (they would otherwise stay up until key expiry).
5. **Google Workspace sessions and tokens**: run RB-GWS-001 steps 1–6 (password reset, sign-out, deprovision,
   delegation, Drive transfer, shared drive managers).
6. **Groups and licences**: remove from all assigned (non-dynamic) groups; dynamic groups follow the disabled
   state. Remove the Microsoft licence after mailbox and OneDrive retention is confirmed (Kestrel uses Google for mail;
   OneDrive holds only Teams files).
7. **Devices**:
   - Mac in Jamf: set the device to **Leaver - Pending Return**; send **Lock** only if the device is not returned within
     5 working days or the leaver is urgent.
   - Windows in Intune: same status via the device category; after return, run **Wipe** and re-use via Autopilot.
   - Mobile apps on personal phones: Intune App Protection selective wipe (**Apps > App selective wipe**).
8. **SaaS apps not behind SSO** (listed in the SaaS register, CF-006): remove accounts manually; note each in the
   ticket.
9. **Privileged access**: if the user had `adm-*` accounts, PIM eligibility or break-glass knowledge, Identity & Access
   removes them and Security Operations rotates any shared secrets they knew.
10. **Hardware return**: courier label for remote leavers; asset record updated in the CMDB with condition.

## Verification

- Entra sign-in logs show only failures (`AADSTS50057: user account is disabled`) after the block time.
- `gam info user` shows OU `/Leavers/Delegated`.
- MeshGate console shows zero active devices for the user.
- Device returned and wiped; CMDB status "In stock" or "Disposed".

## Rollback

If HR cancels a leaver (for example a reversed resignation) within 30 days: re-enable the Entra account, restore
groups from the ticket record, re-register MFA via RB-IDM-001 and move the Google account back to its OU. A completed
Drive transfer is not reversed automatically.

## Escalation

Service Desk owns. Urgent leavers out of hours: page IT on-call (OC-001). Security-sensitive leavers: Security
Operations is added to the ticket before step 2.
