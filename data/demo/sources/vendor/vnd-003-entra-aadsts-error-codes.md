---
id: VND-003
title: Microsoft Entra ID - sign-in error code quick reference (AADSTS codes)
doc_type: vendor
system: entra
owner: Identity & Access
access: it-staff
updated: 2026-10-21
tags: [entra, aadsts, sign-in, error-codes, conditional-access, mfa]
---

# Microsoft Entra ID - sign-in error code quick reference (AADSTS codes)

Kestrel IT's short list of the AADSTS codes that show up in our tickets, with what they usually mean in our tenant and
the runbook to use. Always confirm in the sign-in log (Entra admin center > Monitoring > Sign-in logs) using the
Request ID or Correlation ID from the user's error page.

## How to read the error

The error page shows `AADSTS<number>: <message>`, a Request ID, Correlation ID and timestamp. The sign-in log entry
for that Request ID has the same code in **Basic info > Sign-in error code** plus the Conditional Access and device
tabs. Codes 50xxx are mostly credential and MFA, 53xxx are Conditional Access, 65xxx consent, 7xxxxx application
configuration.

## Credentials and account state

Codes caused by the password or the state of the user object.

## AADSTS50126

Invalid username or password. Repeated failures from unknown IPs are a password spray signal; Security Operations
watches these.

## AADSTS50053

Account locked (smart lockout) after too many failed attempts, or sign-in blocked from a malicious IP. Unlocks after
the lockout period; user can reset via SSPR (KB-0003).

## AADSTS50057

User account is disabled. Expected for leavers (RB-GEN-002). For anyone else, check HR provisioning.

## AADSTS50173 / AADSTS50133

Refresh token or session invalid because the password changed. User signs in again. Seen on Macs after SSPR
(RB-MAC-004).

## AADSTS50034 / AADSTS90072

User does not exist in the tenant, or a guest signing in to the wrong tenant. Check the UPN spelling first.

## MFA

Codes about the second factor or registration of methods.

## AADSTS50076

MFA is required for this sign-in (policy or location) and the client must prompt. Normal on first sign-in; a problem
only if the user has no usable method (RB-IDM-001).

## AADSTS50074

Strong authentication required and not satisfied, often in non-interactive flows. User signs in interactively.

## AADSTS50079

User must register for MFA. If registration itself is blocked by `CA-005-Secure-Registration`, issue a Temporary
Access Pass.

## AADSTS50158

External security challenge not satisfied (for example a third-party or custom control). Rare at Kestrel.

## Conditional Access

Codes where a CA policy decided the outcome. Check the Conditional Access tab in the log entry.

## AADSTS53003

Blocked by Conditional Access. The CA tab shows which policy. Procedure: RB-IDM-002.

## AADSTS53000

Device must be compliant (or the app requires a managed device) and is not, or compliance cannot be read because the
browser does not send device identity. On Mac: Safari/Edge/Chrome with the Enterprise SSO extension; on Windows: Edge
signed in, or Chrome with Windows accounts enabled. Procedure: RB-WIN-002.

## AADSTS53001

Device must be Entra hybrid joined. Kestrel has no hybrid join; seeing this means a misconfigured policy.

## AADSTS530032

Blocked by a security policy (security defaults or a tenant restriction). Escalate to Identity & Access.

## AADSTS70043 / AADSTS700082

Refresh token expired because of sign-in frequency or inactivity. Expected; user signs in again.

## Application configuration

Codes caused by how the app is set up in Entra rather than by the user.

## AADSTS50105

User not assigned to the application ("Assignment required" is on). Request access through the app's access group.

## AADSTS50011

Reply URL mismatch. The redirect or ACS URL the app sent is not configured in the app registration or enterprise app.
Common after a SaaS vendor changes domains.

## AADSTS700016

Application not found in the directory. Wrong tenant or the app was never consented.

## AADSTS65001

Consent required. Kestrel blocks user consent; admins grant consent after the SaaS review (CF-006).

## AADSTS75011

Authentication method mismatch: the SAML app requested a specific authentication context (for example password
only) that does not match how the user signed in. Fix in the app's SAML settings by removing
`RequestedAuthnContext`.

## AADSTS700027

Client assertion signature invalid; a certificate used by a service principal has expired or rotated.
