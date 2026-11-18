---
id: RB-IDM-001
title: Reset authentication methods and force MFA re-registration
doc_type: runbook
system: entra
owner: Identity & Access
access: it-staff
updated: 2026-09-02
tags: [entra, mfa, authenticator, tap, identity-verification]
---

# Reset authentication methods and force MFA re-registration

## Purpose

Let a user who lost, replaced or wiped their phone register MFA again, without weakening the account. Typical
tickets: "new phone, Authenticator empty", "MFA prompt goes to my old phone", repeated `AADSTS50076` (MFA required)
with no way to approve.

## Scope

All Kestrel Entra ID member accounts. Privileged accounts (`adm-*`) are reset only by Identity & Access. Guest accounts
are reset in their home tenant, not ours.

## Prerequisites

- Entra role **Authentication Administrator** (Service Desk L2) or **Privileged Authentication Administrator** for
  admin accounts.
- Identity verification completed (step 1). This is the control that matters; social engineering of the service desk
  is the most common MFA bypass.

## Steps

1. Verify identity: live video call, camera on, user shows company badge or government ID, and you compare with the
   photo in the HR system. Alternatively their line manager confirms on a Slack huddle. Record which method you used
   in the HELP ticket.
2. If the user still has the old phone, send them KB-0011 instead; no reset needed.
3. Review current methods: Entra admin center > **Users > (user) > Authentication methods**, or:
   ```powershell
   Connect-MgGraph -Scopes UserAuthenticationMethod.ReadWrite.All
   Get-MgUserAuthenticationMethod -UserId user@kestrelcloud.example |
     Select-Object Id, @{n='Type';e={$_.AdditionalProperties['@odata.type']}}
   ```
4. Remove the lost device's Authenticator and phone methods:
   ```powershell
   Get-MgUserAuthenticationMicrosoftAuthenticatorMethod -UserId user@kestrelcloud.example
   Remove-MgUserAuthenticationMicrosoftAuthenticatorMethod -UserId user@kestrelcloud.example `
     -MicrosoftAuthenticatorAuthenticationMethodId <id>
   ```
   Do not remove FIDO2 keys or Windows Hello unless they are also lost.
5. Issue a one-time Temporary Access Pass (TAP), valid 60 minutes:
   ```powershell
   New-MgUserAuthenticationTemporaryAccessPassMethod -UserId user@kestrelcloud.example `
     -BodyParameter @{ lifetimeInMinutes = 60; isUsableOnce = $true }
   ```
   Read the TAP to the user on the verified call. Never email it.
6. Revoke sessions so the lost phone loses access:
   ```powershell
   Revoke-MgUserSignInSession -UserId user@kestrelcloud.example
   ```
7. User signs in at `https://aka.ms/mysecurityinfo` with the TAP and follows KB-0001 to add Authenticator
   (passwordless phone sign-in is the Kestrel default).

## Verification

- Authentication methods shows the new Authenticator with today's date.
- Sign-in logs show a successful MFA with "Authentication requirement: Multifactor".
- If the phone was lost, also check RB-SEC-001 for any company data on it (managed apps).

## Rollback

Delete an unused TAP from the user's methods. Methods removed in error cannot be restored; the user re-registers.

## Escalation

Identity & Access for admin accounts, TAP policy errors or `AADSTS50079` loops (registration required but
registration blocked by CA policy `CA-005-Secure-Registration`). Suspected social engineering: stop, do not reset,
report to Security Operations.
