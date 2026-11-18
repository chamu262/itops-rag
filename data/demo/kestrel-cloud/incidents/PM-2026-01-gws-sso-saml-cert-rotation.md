---
id: PM-2026-01
title: Google Workspace SSO outage after SAML signing certificate rotation
doc_type: postmortem
system: gws
owner: Identity & Access
access: it-staff
updated: 2026-03-16
tags: [gws, entra, saml, sso, certificate, outage, change]
---

# PM-2026-01: Google Workspace SSO outage after SAML signing certificate rotation

Blameless post-mortem. Related: CHG-2026-0003, INC0010001.

## Summary

On 2026-03-09 nobody could start a new sign-in to Google Workspace (Gmail, Calendar, Drive) for about 1 hour
20 minutes. The evening before, the SAML signing certificate on the Google Workspace enterprise app in Entra ID
was rotated under CHG-2026-0003. The new certificate was made active in Entra, but it was never uploaded to the
Google SSO profile, so Google rejected every SAML assertion. We fixed it by making the previous certificate
active again in Entra, which rolled the change back.

## Impact

- About 520 staff in Stockholm, London and Lisbon could not sign in to Google services between 06:40 and
  07:58 UTC. Austin was mostly unaffected because of the time zone.
- People who already had a Google session could keep working. Drive for desktop and mobile apps asked users to
  re-authenticate.
- The Service Desk took 63 calls and 41 HELP tickets, including HELP-1038 and HELP-1039.

## Timeline (UTC)

| Time | Event |
|---|---|
| 2026-03-08 20:05 | The change starts. A new SAML signing certificate is created in Entra. |
| 20:12 | The new certificate is made active in Entra. |
| 20:20 | The implementer tries to open the Google Admin console SSO settings. The re-authentication goes through SSO and fails, which nobody spots as a symptom. |
| 20:40 | A test sign-in passes, but only because the browser still had a Google session. The change is marked implemented. |
| 2026-03-09 06:40 | The first SAML errors are reported from Stockholm. |
| 06:58 | A major incident is declared (INC0010001). |
| 07:20 | Identity & Access finds that the certificate thumbprint in Google does not match the active one in Entra. |
| 07:35 | Option 1 is to upload the new certificate to Google. It is blocked because no admin can reach the Admin console without SSO. Option 2 is to roll back in Entra. |
| 07:58 | The previous certificate is active again in Entra. Sign-ins recover. |
| 08:05 | The incident is resolved. |

## Root cause

The procedure activated the new certificate in Entra before Google trusted it. Google then received assertions
signed with a key it did not know. A second problem made it worse: every Google super admin account signed in
through SSO, so the change broke the path we needed to finish or fix the change. The validation step passed by
mistake because it used a cached session instead of a fresh SAML flow.

## What went well

- The previous certificate was still valid, so the rollback was quick and safe.
- The Service Desk spotted the pattern quickly and declared a major incident within 18 minutes of the first report.
- Sign-in logs in Entra showed straight away that authentication succeeded, which pointed us to the trust
  between Entra and Google rather than to the users.

## What went wrong

- The steps were in the wrong order: activate first, upload later.
- We had no Google super admin break-glass account outside SSO.
- The validation step did not require a private browser window or a thumbprint comparison.
- The change ran on a Sunday evening without a second person checking it.

## Action items

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Rewrite the GWS SAML rotation runbook: upload to Google first, then activate in Entra, then test in a private window and compare thumbprints. | Identity & Access | Done |
| 2 | Create two Google super admin break-glass accounts that do not use SSO (excluded from the SSO profile via an org unit), with hardware keys kept in the safe. | Identity & Access | Done |
| 3 | Add a 30-day expiry alert for SAML signing certificates on all enterprise apps. | Identity & Access | Done |
| 4 | Require a second implementer for high-risk identity changes. | Identity & Access | Done |
| 5 | Repeat the rotation with the corrected procedure before 2026-03-31 expiry. Done as a standard change on 2026-03-22; the next rotation followed the same procedure on 2026-09-13. | Identity & Access | Done |
| 6 | Add a Service Desk macro for "Google SAML error" that links to the incident status page. | Service Desk | Done |
