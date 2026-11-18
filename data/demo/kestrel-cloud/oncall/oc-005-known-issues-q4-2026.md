---
id: OC-005
title: Known issues and workarounds - Q4 2026
doc_type: oncall
system: general
owner: Platform SRE
access: it-staff
updated: 2026-11-12
tags: [oncall, known-issues, workarounds, q4-2026]
---

# Known issues and workarounds: Q4 2026

Issues that on-call and the Service Desk will see this quarter, with the agreed workaround. Each item has an owner
team and a tracking ticket. Remove items once fixed and verified. Reviewed in the Monday ops meeting.

## 1. Platform SSO sign-in prompt loops after macOS 27 upgrade

- **Since:** 2026-10-20, Wave 1 of the macOS 27 rollout (RB-MAC-003).
- **Symptom:** "Registration Required" notification reappears after every restart; `app-sso platform -s` shows
  `registrationCompleted: false` although the user completed it.
- **Cause:** Company Portal older than the version that supports the new OS registration flow.
- **Workaround:** Self Service > "Company Portal" (reinstall), restart, then repair registration (RB-MAC-004 step 3).
- **Owner:** Endpoint Engineering, HELP-48511. Fix: Company Portal minimum version enforced in Wave 2 scope.

## 2. MeshGate `MG-202` on some hotel and conference networks

- **Since:** client 4.2.1 (2026-09).
- **Symptom:** connects, but web pages to internal sites hang; small pings work.
- **Workaround:** `meshgate config set mtu 1280` then reconnect; revert with `meshgate config reset mtu` at home.
- **Owner:** Workplace Network, vendor case open. Fix expected in client 4.2.3 (path MTU discovery).

## 3. Kestrel-Corp Wi-Fi certificate not renewed on Macs offline for 90+ days

- **Symptom:** prompt for username/password on Kestrel-Corp (KB-0006).
- **Workaround:** connect via Kestrel-Guest, run Self Service > Update Inventory; if the profile does not reinstall,
  re-enrol (RB-MAC-001).
- **Owner:** Endpoint Engineering, HELP-48302.

## 4. Autopilot `0x800705b4` ESP timeout on the new laptop batch

- **Since:** 2026-11-09, batch of 40 laptops for the January joiner cohort.
- **Cause:** Defender onboarding package plus large driver update during ESP on this model.
- **Workaround:** connect by ethernet for enrolment; if timeout occurs, Autopilot Reset and retry (RB-WIN-001). Second
  attempt succeeds in nearly all cases.
- **Owner:** Endpoint Engineering, INC-2294. Fix: driver update moved out of the ESP blocking phase (CHG-1192).

## 5. Stockholm floor 5 colour printer `KC-STO-PRN-502` drops A3 jobs from Windows

- **Symptom:** A3 jobs released at the printer print on A4 scaled.
- **Workaround:** print to PDF, then print from a Mac, or choose "A3" in the printer's own panel after release.
- **Owner:** Workplace Network, HELP-48107. Driver update planned.

## 6. Google Workspace SAML certificate rotation on 2026-12-03

- **Not a fault yet:** the Entra signing certificate for "Google Workspace (KC)" expires 2026-12-10. Rotation is
  scheduled as CHG-1201 on **2026-12-03 07:00 CET** (low traffic).
- **What on-call should know:** if Google sign-in fails after Entra success on or after 2026-12-03, follow RB-GWS-002
  immediately; treat as SEV1.
- **Owner:** Identity & Access.

## 7. Intune devices "Not evaluated" after long holiday

- **Symptom:** devices offline more than 30 days show Not compliant then Not evaluated after first boot; user blocked
  by `AADSTS53000` for up to an hour.
- **Workaround:** Company Portal > Sync, Check access (RB-WIN-002 step 3). Expect a spike in the first week of January.
- **Owner:** Endpoint Engineering.

## 8. BitLocker recovery prompts after firmware update on one Windows laptop model

- **Symptom:** recovery screen after the October firmware update was installed without BitLocker suspension.
- **Workaround:** provide key (RB-WIN-003), then rotate. Firmware deployment now suspends BitLocker for one reboot.
- **Owner:** Endpoint Engineering, HELP-48420.

## Retired this quarter

- MeshGate `MG-110` for clients below 4.1.0: all clients updated 2026-09-12.
- Jamf Connect "network password and local password are not in sync" after SSPR: resolved by the Platform SSO migration
  for 85% of Macs; remaining Macs follow RB-MAC-004.
