---
id: OC-003
title: First 15 minutes of a SEV1 - checklist
doc_type: oncall
system: general
owner: Platform SRE
access: it-staff
updated: 2026-09-18
tags: [oncall, sev1, incident, checklist, incident-commander]
---

# First 15 minutes of a SEV1

You are the Incident Commander (IC) until you hand over. Your job is to coordinate, communicate and get the right
people in, not to fix it yourself. Severity definitions: CF-005. Who to page: OC-001.

## Minute 0-3: confirm and declare

- [ ] Acknowledge the page.
- [ ] Confirm impact with two independent signals (for example: three or more user reports plus a failing synthetic
      check, or your own reproduction from a clean browser).
- [ ] If it meets SEV1 (office or more than 25% of staff cannot work, or confirmed security incident), **declare it**.
      Do not wait for certainty about the cause.
- [ ] Create the INC ticket (project `INC`), severity SEV1. Note the start time in UTC and CET.

## Minute 3-6: set up the room

- [ ] Create Slack channel `#inc-<number>-<short-name>`, for example `#inc-2301-google-sso`.
- [ ] Start a Google Meet bridge from a personal meeting room and post the link in the channel. If Google Workspace
      itself is down, use the fallback bridge in the on-call vault item "SEV1 fallback bridge" (phone dial-in).
- [ ] Pin a message: IC name (role, not "anyone"), what is broken, current impact, next update time.
- [ ] Start a running timeline in the channel: `HH:MM CET - event`.

## Minute 6-10: page and communicate

- [ ] Page the owning team's on-call from OC-001. For sign-in problems across several apps, page `ia-oncall` first.
- [ ] Security involvement? If anything suggests compromise, page `secops-247` now; they may take command.
- [ ] Post the first update in `#it-status` (and the internal status page):
      ```text
      [SEV1] We are investigating <symptom> affecting <who>. Started ~<time> CET.
      Workaround: <if any>. Next update in 30 minutes.
      ```
- [ ] Notify Head of IT and IT Operations manager via the paging tool's "notify stakeholders" action.
- [ ] Ask the Service Desk (business hours) to put a banner on the HELP portal and tag incoming tickets to the INC.

## Minute 10-15: stabilise

- [ ] What changed? Check the CHG calendar for the last 24 hours, vendor status pages (Microsoft 365 service health,
      Google Workspace status, Jamf status, MeshGate status) and certificate expiry dates (Entra SAML certs,
      APNs, MeshGate controller).
- [ ] Prefer **rollback over fix-forward** if a recent change is the likely cause.
- [ ] Known quick mitigations:
      - Google sign-in failing after Entra success: certificate mismatch, RB-GWS-002.
      - Admins locked out of Entra: break-glass, RB-IDM-003 (Security Operations).
      - All MeshGate gateways unhealthy: check controller certificate and Entra app secret (VND-005, MG-401/MG-503).
      - Many Macs dropped from MDM: APNs certificate (VND-001).
- [ ] Assign a scribe if more than three people are on the bridge.
- [ ] Set the next update time and keep it, even if there is no news.

## Things not to do

- Do not make several changes at once; one change, observe, record.
- Do not edit Conditional Access policies without Identity & Access on the bridge.
- Do not use break-glass accounts for anything other than restoring admin access.
- Do not share customer or personal data in `#it-status`.

## Handing over IC

Say it explicitly on the bridge and in the channel: "<role> is now IC as of HH:MM". Hand over when a more suitable IC
joins, or after 4 hours for fatigue.

## Closing

Resolve when impact has ended and monitoring is clean for 30 minutes. Post the final update, set the INC to
"Resolved", and schedule the post-mortem within 5 business days.
