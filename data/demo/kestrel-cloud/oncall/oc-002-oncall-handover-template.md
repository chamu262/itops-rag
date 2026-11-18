---
id: OC-002
title: On-call handover template and example
doc_type: oncall
system: general
owner: Platform SRE
access: it-staff
updated: 2026-11-10
tags: [oncall, handover, template, rota]
---

# On-call handover template and example

The outgoing on-call fills this in before the Monday 10:00 CET handover call (rota rules: CF-005) and posts it in
`#it-oncall`. The incoming engineer confirms they have read it with a reply. Keep it short; link tickets rather than
copying them.

## Template

```text
On-call handover: week <ISO week>, <outgoing> -> <incoming>

1. Incidents this week
   - INC-<n> <SEV> <one-line summary> - status (resolved / monitoring / open) - PM due <date>

2. Open items the incoming on-call must watch
   - <item> - why it matters - what to do if it fires

3. Changes scheduled during the coming week (CHG)
   - CHG-<n> <date time CET> <summary> - owner team - rollback known? y/n

4. Known issues and workarounds (link OC-005 entries)

5. Alerts that were noisy or wrong
   - <alert> - fired <n> times - action taken / ticket for tuning

6. Access check for incoming
   - [ ] Paging app installed and test page received
   - [ ] PIM roles activatable (Intune, Conditional Access read, Helpdesk Admin)
   - [ ] Jamf, MeshGate console, Google Admin access
   - [ ] Laptop charged, MeshGate working from home

7. Anything else
```

## Filled example

```text
On-call handover: week 46, Workplace on-call (EU) -> Workplace on-call (EU, next)

1. Incidents this week
   - INC-2291 SEV2 MeshGate gw-lon-01 high CPU, users moved to gw-sto-01 for 40 min
     on Tue evening - resolved - PM due 2026-11-14 (Workplace Network)
   - INC-2294 SEV3 Autopilot 0x800705b4 on new laptop batch (ESP timeout,
     Defender onboarding package slow) - monitoring - see OC-005 #4

2. Open items to watch
   - gw-lon-01 kernel patch applied Thu; if CPU > 85% for 10 min the alert
     "MeshGate gateway CPU" fires. Action: drain gateway in console
     (Gateways > gw-lon-01 > Drain), users fail over automatically. Page
     network-oncall only if a second gateway degrades.
   - Two urgent leavers possible Friday evening (HR heads-up in HELP-48812).
     Follow RB-GEN-002; urgent leavers are processed within 30 min.

3. Changes this week
   - CHG-1187 Wed 2026-11-18 19:00 CET Jamf Pro cloud maintenance (vendor) -
     Endpoint Engineering - no rollback needed; Self Service unavailable
     ~30 min.
   - CHG-1190 Thu 2026-11-19 20:00 CET Windows Ring 2 deadline for November
     cumulative update - Endpoint Engineering - rollback: pause ring.

4. Known issues: OC-005 #1 (Platform SSO prompt loop after macOS upgrade),
   #2 (MG-202 on some hotel networks), #6 (Google SAML cert rotation
   prep for 2026-12-03).

5. Noisy alerts
   - "Kestrel-Corp RADIUS auth failures STO" fired 6 times overnight, caused by
     one meeting room device with expired cert (KC-STO-MTR-00118).
     Ticket HELP-48790 to replace cert; alert threshold unchanged.

6. Access check: done on the handover call.

7. Anything else: US evening cover is the US on-call this week as normal.
   Phone line forwarding tested Monday 09:30, OK.
```

## Tips

- If you were paged at night and lost sleep, say so; the incoming on-call or lead can take the morning queue.
- Unresolved SEV1/SEV2 incidents are handed over on a call, never only in writing.
- Anything that should become a runbook: note it under 7 and create a HELP ticket for the owning team.
