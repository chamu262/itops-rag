---
id: OC-001
title: IT escalation matrix by system
doc_type: oncall
system: general
owner: Platform SRE
access: it-staff
updated: 2026-10-06
tags: [oncall, escalation, matrix, paging, vendors]
---

# IT escalation matrix by system

Who to involve, in what order, when something breaks. Severity definitions are in CF-005. Paging is done from the
paging tool's service names below; do not phone people's personal numbers unless the paging tool itself is down
(then use the printed contact sheet in the on-call 1Password vault item "Paging fallback").

## How to use

1. Find the system. Page the **L2 on-call service** for SEV1 and SEV2 out of hours; in business hours post in the team
   channel and assign the INC ticket.
2. If no acknowledgement within the time in CF-005 (15 min SEV1, 30 min SEV2), the paging tool escalates to the
   **L3** automatically. Page manually if you are already on a bridge.
3. Vendor support is opened by the owning team, not by the Service Desk, except where noted.

## Matrix

| System | Owner team | L2 on-call service | L3 escalation | Vendor path | Typical SEV1/2 triggers |
|---|---|---|---|---|---|
| Entra ID, Conditional Access, MFA | Identity & Access | `ia-oncall` | Identity & Access lead | Microsoft Unified support, Severity A for tenant-wide | Sign-in outage, CA lockout, MFA failures |
| Break-glass procedure | Security Operations | `secops-247` | Head of IT | Microsoft (Sev A) | Admin lockout (RB-IDM-003) |
| Google Workspace (mail, Drive, Meet, SSO) | Collaboration Tools | `collab-oncall` | Collaboration Tools lead; Identity & Access for SSO | Google Workspace support, P1 via admin console | SSO broken (RB-GWS-002), mail flow stopped |
| Jamf Pro (Macs, iPhones) | Endpoint Engineering | `endpoint-oncall` | Endpoint Engineering lead | Jamf support (premium), cloud status page | APNs or ADE token expired, mass unenrolment |
| Intune and Autopilot | Endpoint Engineering | `endpoint-oncall` | Endpoint Engineering lead | Microsoft Unified support | Compliance flip, Autopilot service outage |
| MeshGate VPN | Workplace Network | `network-oncall` | Workplace Network lead | MeshGate vendor support, 24/7 for P1 | Gateways down (MG-503), mass MG-401 |
| Office LAN, Wi-Fi, printers | Workplace Network | `network-oncall` | Workplace Network lead | ISP per office (contract numbers in vault) | Office offline, Kestrel-Corp RADIUS down |
| Defender for Endpoint, phishing, lost devices | Security Operations | `secops-247` | CISO | Microsoft (security) | Malware outbreak, account compromise |
| Paging tool, monitoring, status page | Platform SRE | `sre-primary` | Platform SRE lead | Vendor status page | Alerts not delivered |
| Service Desk tooling (HELP portal, phone line) | Service Desk | `sd-lead` (business hours) | IT Operations manager | Telephony provider | Phone line down |

## Cross-team rules

- **Identity first.** Any incident where more than one system fails at the same time with sign-in errors: page
  `ia-oncall` before others; most multi-system outages at Kestrel are identity.
- **Security takes over** when a suspected compromise is found. The IC hands command to Security Operations and keeps
  a technical role.
- **Office facility issues** (power, building access, AV furniture) go to the local office team, not IT on-call.
- **Platform SRE** is informed of SEV1 incidents even if they are not involved, because customer-facing status may be
  affected.

## Management notification

| Severity | Notify | When |
|---|---|---|
| SEV1 | Head of IT, IT Operations manager | Immediately, by phone via the paging tool |
| SEV2 | IT Operations manager | Within 1 hour |
| SEV3/4 | Not required | Weekly ops review |

## Keeping this current

Team leads review this page quarterly. Last review: 2026-10-06. Changes to paging services must be reflected here in
the same week.
