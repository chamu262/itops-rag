---
id: RB-GWS-002
title: Google Workspace SAML SSO broken after Entra certificate rotation
doc_type: runbook
system: gws
owner: Identity & Access
access: it-staff
updated: 2026-11-04
tags: [gws, entra, saml, sso, certificate, federation]
---

# Google Workspace SAML SSO broken after Entra certificate rotation

## Purpose

Restore sign-in to Google Workspace when Entra ID's SAML signing certificate for the Google enterprise application
was rotated but Google still holds the old certificate. Everyone signing in to Gmail, Calendar or Drive is affected,
so this is usually a SEV1 (CF-005). Settings background: VND-004 and CF-002.

## Symptoms

- Users are redirected from `accounts.google.com` to Entra, sign in and MFA successfully, then Google shows an
  error page such as "Invalid SAML response" or "We could not verify the signature of the login response".
- Already signed-in browser sessions keep working until they expire, so reports grow over the morning.
- Entra sign-in log shows **Success** for app "Google Workspace (KC)". The failure is on the Google side.

## Prerequisites

- Entra role **Application Administrator** and Google Admin **Super Admin** (Identity & Access on-call holds both
  through PIM and Google admin delegation).
- A Google super admin account that does **not** use SSO: `gws-sa-01@kestrelcloud.example` is in OU `/IT/SSO-Bypass`,
  where the SSO profile is not assigned.

## Steps

1. Confirm the cause. In Entra: **Enterprise applications > Google Workspace (KC) > Single sign-on > SAML
   Certificates**. Note the **Active** certificate thumbprint and its activation date.
2. Sign in to `https://admin.google.com` as the bypass super admin. Go to **Security > Authentication > SSO with
   third-party IdP > Third-party SSO profiles > Entra-KC**. Compare the certificate expiry/fingerprint with step 1.
3. In Entra download **Certificate (Base64)** of the active certificate.
4. In Google upload it under **Verification certificate > Replace certificate**, then **Save**. Google accepts one
   certificate per profile, so the switch is immediate.
5. Test in a private window with a normal pilot account. Sign-in should complete without error.
6. Post an update in the incident channel: users who still fail must close all browser windows or sign out of Google
   and back in.

## Prevention

- Entra emails the notification list (`it-identity@kestrelcloud.example`) 60, 30 and 7 days before expiry.
- Rotation is a planned change: create the new certificate in Entra as **Inactive**, raise a CHG, then at the agreed
  time make it **Active** in Entra and upload it to Google within the same five-minute window.
- The next planned rotation is listed in OC-005.

## Verification

- Pilot users and a sample from each office sign in successfully.
- Google Admin > Reporting > Audit > SAML log shows successful events and no `failure_type` entries after the fix.

## Rollback

If the new certificate causes failures, set the previous certificate back to **Active** in Entra (it remains listed
until deleted) and upload it again to Google.

## Escalation

Identity & Access on-call owns. Collaboration Tools assists with user comms. If the bypass super admin cannot sign in,
use the second bypass account `gws-sa-02@kestrelcloud.example`; credentials are in the Security Operations vault.
