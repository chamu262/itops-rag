---
id: PM-2026-02
title: MeshGate EU outage after gateway upgrade to 5.0
doc_type: postmortem
system: meshgate
owner: Workplace Network
access: it-staff
updated: 2026-05-26
tags: [meshgate, vpn, mg-503, upgrade, outage, change]
---

# PM-2026-02: MeshGate EU outage after gateway upgrade to 5.0

Blameless post-mortem. Related: CHG-2026-0005, INC0010002.

## Summary

On 2026-05-19, EU users could not connect to MeshGate for about 90 minutes at the start of the business day.
Clients showed **MG-503 Gateway unavailable**. The night before, both EU gateways had been upgraded from 4.9.3
to 5.0. The 5.0 config template did not define the WireGuard UDP 51820 listener, so the gateways accepted
nothing except TCP 443 fallback, and that fallback was off for most user groups. We restored both gateways from
VM snapshots, which rolled them back to 4.9.3.

## Impact

- About 300 remote EU users had no access to internal systems (wiki, staging, admin tools) between 06:00 and
  07:30 UTC.
- Users in the office were unaffected because they did not need MeshGate on the office network.
- Austin users were unaffected because the US gateways were not upgraded.

## Timeline (UTC)

| Time | Event |
|---|---|
| 2026-05-18 22:05 | gw-euw-01 is drained and upgraded to 5.0, and config template v5 is applied. |
| 22:30 | The test client connects. Unknown to the tester, it is using TCP 443 fallback. |
| 22:45 | gw-eun-01 is upgraded the same way. |
| 23:10 | The change is marked implemented. Both gateways show as healthy in the admin UI. |
| 2026-05-19 06:00 | MG-503 reports start as Stockholm staff begin work. |
| 06:10 | INC0010002 is opened. |
| 06:15 | The gateways look healthy over HTTPS, but there are no WireGuard handshakes. |
| 06:50 | `ss -lun` shows no UDP 51820 listener on either gateway. |
| 07:05 | We decide to roll back rather than hand-edit the v5 template under pressure. |
| 07:30 | Both gateways are restored from snapshot and clients reconnect. |
| 07:45 | The incident is resolved. |

## Root cause

MeshGate 5.0 moved listener definitions from an implicit default into an explicit `listeners:` block in the
config template. The v5 template we built from the vendor sample only had the TCP 443 listener. The upgrade
checklist only checked the admin UI and one test client, and that client had TCP fallback turned on, so the
missing UDP path was never tested. We also upgraded both EU gateways in the same window, which left no
working EU gateway to fail over to.

## What went well

- VM snapshots were taken and the restore was quick.
- The Service Desk's MG-503 checklist sent tickets straight to Workplace Network and not to device
  troubleshooting.
- The US gateways stayed on the old version, which confirmed the version difference fast.

## What went wrong

- Both gateways in one region were upgraded in the same window.
- The test client did not match a normal user configuration.
- Nobody diffed the v4 and v5 config templates.
- MeshGate gateways had no synthetic UDP handshake monitor.

## Action items

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Add a synthetic WireGuard handshake probe (UDP only) for every gateway, alerting to on-call. | Platform SRE | Done |
| 2 | Upgrade policy: one gateway per region per day, leave it in service for one business day before the next. | Workplace Network | Done |
| 3 | Keep a dedicated test client profile with TCP fallback disabled. | Workplace Network | Done |
| 4 | Diff config templates between major versions and get peer review. | Workplace Network | Done |
| 5 | Re-plan the 5.0 upgrade with an explicit UDP 51820 listener; canary on gw-euw-01. | Workplace Network | In progress |
| 6 | Turn on TCP 443 fallback by default for all user groups as a resilience measure. | Workplace Network | Done |
