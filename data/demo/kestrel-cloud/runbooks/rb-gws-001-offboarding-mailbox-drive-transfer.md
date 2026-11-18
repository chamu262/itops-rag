---
id: RB-GWS-001
title: Mailbox delegation and Drive ownership transfer at offboarding
doc_type: runbook
system: gws
owner: Collaboration Tools
access: it-staff
updated: 2026-08-11
tags: [gws, offboarding, gmail, delegation, drive, shared-drives, gam]
---

# Mailbox delegation and Drive ownership transfer at offboarding

## Purpose

Keep a leaver's mail and files available to their manager while the account is shut down. This is step 6 of the
leaver checklist RB-GEN-002.

## Scope

Google Workspace accounts in `kestrelcloud.example`. Mail delegation lasts 30 days; Drive transfer is permanent.
Legal hold cases (Vault matter open) need Security Operations sign-off before any change.

## Prerequisites

- Google Admin role **KC User Lifecycle Admin** (users, data transfer, Gmail delegation) and GAM configured on the
  Collaboration Tools admin workstation.
- The account has already been blocked at the IdP (RB-GEN-002 step 2). Do not suspend the Google account yet:
  Gmail delegation and data transfer need an active account.
- HELP ticket with manager name and the agreed delegate (usually the manager).

## Steps

1. Reset password and kill sessions on the Google side (Entra block alone does not end existing Google sessions):
   ```bash
   gam update user leaver@kestrelcloud.example password random changepassword off
   gam user leaver@kestrelcloud.example signout
   gam user leaver@kestrelcloud.example deprovision   # removes app passwords, OAuth tokens, backup codes
   ```
2. Delegate the mailbox to the manager:
   ```bash
   gam user leaver@kestrelcloud.example add delegate manager@kestrelcloud.example
   gam user leaver@kestrelcloud.example show delegates
   ```
   The manager sees the mailbox under their account switcher within an hour.
3. Set an auto-reply (agreed wording in the ticket):
   ```bash
   gam user leaver@kestrelcloud.example vacation on subject "No longer at Kestrel Cloud" \
     message "Please contact manager@kestrelcloud.example." 
   ```
4. Transfer My Drive files (owned files go into a folder named after the leaver in the manager's My Drive):
   ```bash
   gam create datatransfer leaver@kestrelcloud.example gdrive manager@kestrelcloud.example privacy_level shared,private
   gam print datatransfers olduser leaver@kestrelcloud.example
   ```
   Wait for status `completed`. Calendar events are transferred with the `calendar` application in the same way.
5. Shared drives: files there are owned by the shared drive, so nothing is lost. But if the leaver was the only
   **Manager** of a shared drive, add a new one:
   ```bash
   gam user leaver@kestrelcloud.example print shareddrives fields id,name
   gam user leaver@kestrelcloud.example print drivefileacls <sharedDriveId> 
   gam add drivefileacl <sharedDriveId> user manager@kestrelcloud.example role organizer
   ```
6. Move the user to OU `/Leavers/Delegated` (licence "Archived User" applies after 30 days via the leavers job).
7. After 30 days: remove delegation, export to Vault if required, delete the account. Aliases are added to the
   manager's account only on request.

## Verification

- `gam info user leaver@kestrelcloud.example` shows the new OU and no active tokens.
- Manager confirms they can open the mailbox and the transferred folder "leaver@kestrelcloud.example Files".

## Rollback

Delegation: `gam user leaver@... delete delegate manager@...`. A completed Drive transfer cannot be undone with a
single command; ownership must be moved back file by file, so confirm the recipient before step 4.

## Escalation

Collaboration Tools. Transfer stuck in `inProgress` for more than 48 hours: open a Google support case. Requests to
give anyone other than the manager access to a leaver's mail need HR and Security Operations approval.
