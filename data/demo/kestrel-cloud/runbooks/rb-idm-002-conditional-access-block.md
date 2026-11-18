---
id: RB-IDM-002
title: Troubleshoot a Conditional Access block (AADSTS53003)
doc_type: runbook
system: entra
owner: Identity & Access
access: it-staff
updated: 2026-10-21
tags: [entra, conditional-access, aadsts53003, sign-in, troubleshooting]
---

# Troubleshoot a Conditional Access block (AADSTS53003)

## Purpose

Find out which Conditional Access (CA) policy blocked a sign-in and fix the cause instead of excluding the user.
The user sees "You cannot access this right now" with **`AADSTS53003: Access has been blocked by Conditional Access
policies`**. Related codes are in VND-003.

## Scope

Interactive and non-interactive sign-ins to Kestrel's Entra tenant, including SAML apps such as Google Workspace.

## Prerequisites

- Entra role **Security Reader** or **Conditional Access Administrator** (read-only use is enough for diagnosis).
- The user's UPN, approximate time, app and the **Correlation ID / Request ID** from "More details" on the error page.

## Kestrel CA policies most often involved

| Policy | Effect |
|---|---|
| `CA-001-Block-Legacy-Auth` | Blocks IMAP/POP/basic auth clients |
| `CA-003-Block-Unsupported-Countries` | Blocks sign-ins from countries outside the allowed list |
| `CA-005-Secure-Registration` | Security info registration only from compliant device or with TAP |
| `CA-020-Require-Compliant-Device` | Office apps, GWS, MeshGate require Intune or Jamf compliant device (`AADSTS53000` if not) |
| `CA-030-Admin-Phishing-Resistant` | Admin roles need FIDO2 |
| `CA-040-High-User-Risk-Block` | Blocks users with risk "High" |

## Steps

1. Entra admin center > **Monitoring > Sign-in logs**, filter by user and the Request ID. Open the failed entry.
2. Tab **Conditional Access**: find the policy with result **Failure**. Tab **Basic info** shows the failure reason;
   **Device info** shows Compliant/Managed and join type; **Location** shows IP and country.
3. Or query via Graph:
   ```powershell
   Get-MgAuditLogSignIn -Filter "userPrincipalName eq 'user@kestrelcloud.example' and status/errorCode eq 53003" -Top 5 |
     Select CreatedDateTime, AppDisplayName, IpAddress, @{n='Policies';e={($_.AppliedConditionalAccessPolicies |
     ? Result -eq 'failure').DisplayName}}
   ```
4. Act on the cause:
   - **Country block**: user is travelling. Business travel exceptions use group `SG-CA-Travel-<ISO>` with an end
     date; requires manager approval in the ticket. Note: IPs from MeshGate gateways (203.0.113.10, 203.0.113.20,
     198.51.100.10, 198.51.100.20) are a trusted named location; connecting MeshGate first often avoids the block.
   - **Legacy auth**: find the client in "Client app"; move the user to a modern client (KB-0012 for mobile mail).
   - **Device not compliant/registered**: RB-WIN-002 (Windows) or RB-MAC-001 (Mac).
   - **User risk High**: hand to Security Operations; they confirm compromise or dismiss risk.
5. Use the **What If** tool (Conditional Access > Policies > What If) with the same user, app, platform and location
   to confirm the fix before asking the user to retry.

## Verification

New sign-in entry shows Success and the expected policies as "Success" or "Not applied".

## Rollback

Remove temporary group memberships (`SG-CA-Travel-*`, `SG-CA-Compliance-Exception`) on their end date. Service Desk
must not edit CA policies.

## Escalation

Identity & Access. If many users are blocked at once after a policy change, roll back the change per the CHG record
and declare SEV2 (CF-005). Never use break-glass accounts (RB-IDM-003) for a single-user block.
