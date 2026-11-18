---
id: RB-NET-001
title: MeshGate VPN client cannot connect (MG-401, MG-503 and others)
doc_type: runbook
system: meshgate
owner: Workplace Network
access: it-staff
updated: 2026-10-29
tags: [meshgate, vpn, remote-access, wireguard, mg-401, mg-503]
---

# MeshGate VPN client cannot connect

## Purpose

Get a user back on MeshGate when the client shows an error. Full code list: VND-005. End-user setup: KB-0002.

## Scope

MeshGate client 4.x on macOS and Windows. Controller: `https://meshgate.kestrelcloud.example`. Gateways:
`gw-sto-01` (203.0.113.10), `gw-lon-01` (203.0.113.20), `gw-aus-01` (198.51.100.10), `gw-lis-01`
(198.51.100.20), all under `meshgate.kestrelcloud.example`. Tunnel address space `10.40.0.0/16`.

## Prerequisites

- MeshGate admin console role **Support** (Service Desk L2) or **Network Admin**.
- User's device name and approximate time of the failure.

## Steps

1. Collect client state:
   ```bash
   meshgate status
   meshgate diag --bundle   # writes meshgate-diag-<date>.zip to the Desktop
   ```
   Logs: macOS `/Library/Logs/MeshGate/meshgate.log`, Windows `C:\ProgramData\MeshGate\logs\meshgate.log`.
2. Match the error:

   **MG-401 Authentication failed / token rejected**
   - Entra token expired or user password changed. Run `meshgate logout && meshgate login`; the browser sign-in
     opens.
   - If sign-in shows an AADSTS code, follow RB-IDM-002 (CA) or RB-IDM-001 (MFA).
   - Check the clock: skew over 5 minutes causes MG-401 with `reason=token_not_yet_valid`.

   **MG-403 Not authorised**
   - User not in `SG-MeshGate-Users` (or the team group for restricted segments). Joiners get it automatically via
     the HR-driven dynamic group within 2 hours of start time.

   **MG-301 / MG-302 Posture check failed**
   - Device not compliant or OS below minimum. Fix compliance: RB-WIN-002 or RB-MAC-001; OS: RB-MAC-003.

   **MG-201 Handshake timeout**
   - UDP 51820 blocked (hotels, some guest networks). Client should fall back to TCP 443 automatically; confirm
     `transport: tcp-443` in `meshgate status`. Force it with `meshgate config set transport tcp443`.

   **MG-503 Gateway unavailable**
   - Check the admin console **Gateways** page. If one gateway is down, move the user:
     `meshgate connect --gateway gw-lon-01`. If all gateways show unhealthy, it is a service issue.
3. Re-test with `meshgate ping 10.40.0.1` (gateway tunnel address) and open `https://intranet.kestrelcloud.example`.

## Verification

`meshgate status` shows `state: connected`, a 10.40.x.x address and handshake younger than 2 minutes.

## Rollback

Revert any per-user transport or gateway override after the user is back on a normal network:
`meshgate config reset transport`.

## Escalation

Workplace Network. MG-503 for more than one gateway, or MG-401 for many users at once (possible Entra or controller
certificate issue), is a SEV2; page Workplace Network on-call (OC-001).
