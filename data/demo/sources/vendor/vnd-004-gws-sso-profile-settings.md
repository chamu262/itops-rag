---
id: VND-004
title: Google Workspace - admin console SSO profile settings
doc_type: vendor
system: gws
owner: Collaboration Tools
access: it-staff
updated: 2026-11-04
tags: [gws, saml, sso, entra, federation, admin-console]
---

# Google Workspace - admin console SSO profile settings

Kestrel IT's notes on how Google Workspace is configured to use Entra ID as the identity provider, and which settings
matter when SSO breaks. Architecture context: CF-002. Incident procedure: RB-GWS-002.

## Overview

Google Workspace (`kestrelcloud.example`) accepts SAML 2.0 assertions from Entra ID. Users and groups are
provisioned into Google by Entra SCIM provisioning. Passwords are not synchronised to Google; Google never sees the
Kestrel password.

## SSO profile

Google Admin > **Security > Authentication > SSO with third-party IdP**. Kestrel uses a named SSO profile, not the
legacy organisation-wide profile.

| Setting | Kestrel value |
|---|---|
| Profile name | `Entra-KC` |
| IdP entity ID | `https://sts.windows.net/<tenant-id>/` |
| Sign-in page URL | `https://login.microsoftonline.com/<tenant-id>/saml2` |
| Sign-out page URL | `https://login.microsoftonline.com/<tenant-id>/saml2` |
| Change password URL | `https://mysignins.microsoft.com/security-info/password/change` |
| Verification certificate | Base64 SAML signing certificate from the Entra enterprise app (one certificate only) |
| Use a domain-specific issuer | Off |

The **SP details** Google shows for the profile (entity ID and ACS URL in the form
`https://accounts.google.com/samlrp/<profile-id>/acs`) must match the Entra enterprise app **Identifier** and **Reply
URL**. Mismatch produces `AADSTS50011` on the Entra side.

## Profile assignment

**Manage SSO profile assignments** decides who uses SSO:

- Root OU `/`: `Entra-KC`.
- `/IT/SSO-Bypass`: **None** (Google passwords). Contains only the two break-glass super admins
  `gws-sa-01` and `gws-sa-02`. These accounts have hardware security keys enforced by Google 2-Step Verification.
- Super admins are not redirected to SSO when signing in at `admin.google.com` directly; they still need 2SV.

## Network masks

Not used. Kestrel does not limit SSO by network; Entra Conditional Access controls where and how users sign in.

## Certificate handling

- Entra SAML signing certificates are valid for 3 years at Kestrel. Expiry notifications go to
  `it-identity@kestrelcloud.example`.
- Google accepts only one verification certificate per profile. There is no overlap window, so the Entra activation
  and Google upload must be done together in one change.
- The SAML signing option in Entra is **Sign SAML assertion**, algorithm SHA-256.

## Claims from Entra

| Claim | Source |
|---|---|
| NameID (format: emailAddress) | `user.userprincipalname` |

No other claims are required. UPN must equal the Google primary email; renames must be done in Entra first and then
flow through SCIM.

## Troubleshooting signals

- Google Admin > **Reporting > Audit and investigation > SAML log events**: shows success and failure type per sign-in
  attempt, including signature and timing failures.
- Timing failures: Entra assertions are valid for a short window. Timing failures in the SAML log usually mean the
  user replayed an old browser tab or the sign-in took several minutes; ask them to start again from Gmail.
- A user can sign in to Entra (success in Entra sign-in log) but not Google: almost always the certificate or the ACS
  URL on the Google side.
- `AADSTS50105` on the Entra page means the user is not assigned to the Google enterprise app; check that they are in
  the assignment group `SG-App-GoogleWorkspace`.

## Changes

All changes to the SSO profile need a CHG record and are made by Identity & Access with Collaboration Tools present.
