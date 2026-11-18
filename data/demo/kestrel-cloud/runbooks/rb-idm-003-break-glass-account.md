---
id: RB-IDM-003
title: Use an Entra break-glass (emergency access) account
doc_type: runbook
system: entra
owner: Security Operations
access: security
updated: 2026-05-27
tags: [entra, break-glass, emergency-access, privileged, security]
---

# Use an Entra break-glass (emergency access) account

## Purpose

Regain administrative control of the Kestrel Entra tenant when normal admin sign-in is impossible: a Conditional
Access misconfiguration locking out all admins, MFA service outage, or federation failure. Break-glass use is always
a SEV1 (CF-005).

## Scope

Two cloud-only accounts: `bg-admin-01@kestrelcloud.example` and `bg-admin-02@kestrelcloud.example`. Both hold Global
Administrator permanently, are excluded from all CA policies except `CA-000-BreakGlass-FIDO2-Only`, and authenticate
with FIDO2 security keys only.

## Prerequisites

- Approval from two of: Head of IT, Security Operations lead, Identity & Access lead (verbal on the SEV1 bridge is
  sufficient, recorded in the incident timeline).
- Physical access to a key safe: Stockholm office server room safe S-2 (keys for bg-admin-01) or London office safe
  L-1 (keys for bg-admin-02). Safe codes are held in the sealed envelope process owned by Security Operations.
- A clean, compliant admin workstation (not a personal device).

## Steps

1. Declare SEV1 and open the incident channel `#inc-<number>`; state "break-glass in use" in the first message.
2. Two people retrieve the FIDO2 key from the safe and log the seal number in the safe register.
3. Sign in at `https://entra.microsoft.com` in a private browser window as the break-glass account using the key.
   Expect `AADSTS50076` only if the FIDO2 policy is broken; in that case try the second account.
4. Do the minimum change that restores normal admin access, for example disable the faulty CA policy or set it to
   **Report-only**. Record every change with timestamp in the incident timeline.
5. Confirm a named admin can sign in again with their own account, then **sign out** of the break-glass session.
6. Within 24 hours:
   - Return the key to the safe with a new tamper seal; record the new seal number.
   - Security Operations reviews Entra audit and sign-in logs for the break-glass account and attaches them to the INC.
   - Write a post-mortem (PM-) covering why normal access failed.

## Monitoring

Any sign-in by either account raises a Sentinel alert `BreakGlass-SignIn` to Security Operations on-call within five
minutes. An alert without an open SEV1 is treated as a security incident.

## Verification

- Admin access restored for named admins.
- Audit log shows only the changes recorded in the timeline.
- Quarterly test (first Tuesday of Jan, Apr, Jul, Oct) passes: sign in, verify Global Administrator, sign out.

## Rollback

Revert any temporary change made under break-glass once normal admins have access, through a normal CHG.

## Escalation

Security Operations on-call owns the process. Identity & Access joins for any CA or authentication method change.
If both accounts fail, open a Severity A case with Microsoft support from the bridge.
