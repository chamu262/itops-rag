---
id: PM-2026-03
title: Mass Mac and iPhone MDM outage after APNs certificate expired
doc_type: postmortem
system: jamf
owner: Endpoint Engineering
access: it-staff
updated: 2025-12-04
tags: [jamf, apns, mdm, certificate, macos, ios, outage]
---

# PM-2026-03: Mass Mac and iPhone MDM outage after APNs certificate expired

Blameless post-mortem. Related: INC0010003. (Numbered in the 2026 series because it was reviewed in the
2026 planning cycle; the incident happened in November 2025.)

## Summary

The Apple Push Notification service (APNs) certificate that Jamf Pro uses to wake devices expired at 23:59
UTC on 2025-11-26. For about 13 hours Jamf could not send MDM commands to any Mac, iPhone or iPad.
Configuration profiles, lock and wipe commands, and DDM updates queued up without being delivered. Policies
that run on the Jamf agent check-in kept working, so the outage was not obvious at first. We renewed the
certificate with the same Managed Apple Account, so no device had to re-enrol.

## Impact

- About 520 Macs and 180 iOS devices received no MDM commands between 2025-11-26 23:59 and 2025-11-27 13:10
  UTC.
- A lost-device lock request (Service Desk) was delayed by 4 hours.
- New Wi-Fi certificate profiles and a FileVault escrow fix were delayed.
- If the certificate had been replaced with a new one (a different Apple account or topic) instead of
  renewed, every device would have needed re-enrolment. That was avoided.

## Timeline (UTC)

| Time | Event |
|---|---|
| 2025-10-27 | Apple sends the 30-day expiry reminder to the Managed Apple Account's contact address, a former team member's mailbox that now forwards to nobody. |
| 2025-11-26 23:59 | The APNs certificate expires. |
| 2025-11-27 07:50 | Endpoint Engineering notices a growing "pending commands" count in Jamf. |
| 08:30 | INC0010003 is opened and the Jamf banner confirms the expired push certificate. |
| 08:45–10:20 | We look for the Managed Apple Account that owns the certificate. Its credentials are found in the shared team vault, and its MFA device is the team phone. |
| 11:05 | The certificate is renewed in Apple's push certificates portal and uploaded to Jamf Pro. A test push succeeds. |
| 13:10 | 96% of devices have checked in and the incident is resolved. |

## Root cause

The renewal depended on an email reminder sent to one person's address. When that person left, nobody moved
the reminder to someone else. Jamf shows an expiry warning in the console, but nobody looked at it routinely,
and no automated alert covered the APNs certificate expiry date.

## What went well

- The account details were in the shared vault and the MFA was on a team device, not a personal phone.
- The engineer checked that the certificate was being *renewed* with the same account and topic, which avoided
  a full re-enrolment.
- Agent-based policies kept working, so patching and inventory went on.

## What went wrong

- No monitoring on certificate expiry for Apple-related services (APNs, ADE token, VPP token).
- The ownership record for the Apple account was out of date.
- Finding the right account took about 1.5 hours.

## Action items

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Add the APNs certificate, ADE token and VPP token expiry dates to the certificate expiry monitor, alerting at 60/30/7 days to a shared mailbox and on-call. | Platform SRE | Done |
| 2 | Change the Managed Apple Account contact address to a shared team mailbox. | Endpoint Engineering | Done |
| 3 | Write an APNs renewal runbook with screenshots that stresses "renew, do not create new". | Endpoint Engineering | Done |
| 4 | Add an Apple account ownership review to the leaver checklist for IT staff. | Service Desk | Done |
| 5 | Add a pending MDM command count to the Jamf health dashboard. | Endpoint Engineering | In progress |
