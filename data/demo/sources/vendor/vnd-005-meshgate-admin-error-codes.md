---
id: VND-005
title: MeshGate VPN - administrator guide - error codes MG-1xx to MG-5xx
doc_type: vendor
system: meshgate
owner: Workplace Network
access: it-staff
updated: 2026-10-29
tags: [meshgate, vpn, error-codes, wireguard, posture, admin]
---

# MeshGate VPN - administrator guide: error codes MG-1xx to MG-5xx

Kestrel IT's summarised notes on MeshGate client and controller error codes. MeshGate is a WireGuard-based mesh VPN:
the client authenticates to the controller with an Entra ID OIDC token, passes a device posture check, receives a
short-lived WireGuard key and peers with the nearest healthy gateway. Procedure: RB-NET-001. User guide: KB-0002.

## Code families

| Range | Area |
|---|---|
| MG-1xx | Client installation and local configuration |
| MG-2xx | Network path and WireGuard handshake |
| MG-3xx | Device posture |
| MG-4xx | Authentication and authorisation |
| MG-5xx | Controller and gateway service |

## MG-1xx client

- **MG-101 Invalid configuration**: the managed config (`/Library/Managed Preferences/com.meshgate.client.plist` or
  registry `HKLM\SOFTWARE\Policies\MeshGate`) is missing or malformed. Re-push the Jamf profile `KC-MeshGate-Config` or
  the Intune configuration.
- **MG-102 Network extension not approved** (macOS): system extension blocked. Check the system extension profile
  `KC-MeshGate-SysExt` is installed; `systemextensionsctl list` should show the extension `activated enabled`.
- **MG-110 Client version not supported**: controller minimum is 4.1.0 from 2026-09-01. Update via Self Service /
  Company Portal.
- **MG-120 Local key store error**: keychain or DPAPI entry corrupt. `meshgate reset --keys` and sign in again.

## MG-2xx network

- **MG-201 Handshake timeout**: no WireGuard handshake within 15 s on UDP 51820. Client falls back to TCP 443
  (WireGuard over TLS) automatically unless `transport` is pinned. Typical on hotel and guest networks.
- **MG-202 MTU / fragmentation**: tunnel up but large packets fail. Default MTU 1380; on PPPoE or nested VPN use
  `meshgate config set mtu 1280`.
- **MG-203 DNS resolution failed for controller**: client cannot resolve `meshgate.kestrelcloud.example`. Check local
  DNS or captive portal.
- **MG-210 Split tunnel route conflict**: home network uses an overlapping 10.40.0.0/16 range. Workaround: client
  setting `tunnel.cgnat_remap=true`.

## MG-3xx posture

- **MG-301 Device not compliant / not managed**: compliance from Intune (Windows) or Jamf device compliance (Mac) is not
  "Compliant", or the device is unknown. Fix compliance first (RB-WIN-002, RB-MAC-001).
- **MG-302 OS below minimum**: Kestrel minimum is macOS 26.5 and Windows 11 23H2 with the latest cumulative update
  minus one.
- **MG-303 Disk encryption off**: FileVault or BitLocker not reported as on.
- **MG-310 Posture data stale**: device has not reported to the MDM in 7 days.

## MG-4xx authentication and authorisation

- **MG-401 Authentication failed**: OIDC token rejected. Sub-reasons in the client log: `token_expired`,
  `token_not_yet_valid` (clock skew over 300 s), `invalid_audience` (wrong tenant), `password_changed`. A wave of MG-401
  for many users points to the controller's Entra app registration secret or certificate.
- **MG-402 MFA claim missing**: token issued without MFA. Check the Entra CA policy targeting the MeshGate app.
- **MG-403 Not authorised**: user not in `SG-MeshGate-Users`, or requested segment not allowed by ACL.
- **MG-404 Device revoked**: device was revoked by an admin (leaver, lost device). Re-register only with a ticket.
- **MG-429 Too many attempts**: rate limit, 10 sign-ins per 5 minutes per device.

## MG-5xx service

- **MG-500 Controller internal error**: collect `meshgate diag --bundle`, open a vendor case.
- **MG-502 Controller unreachable**: controller API down or blocked. Check status page and firewall.
- **MG-503 Gateway unavailable**: selected gateway unhealthy or at capacity (2,000 peers per gateway). Client retries the
  next nearest gateway after 20 s.
- **MG-504 Gateway timeout**: gateway did not answer the peer setup in time; often a gateway under high CPU.

## Admin console quick checks

- **Gateways**: health, peer count and CPU per gateway (`gw-sto-01`, `gw-lon-01`, `gw-aus-01`, `gw-lis-01`).
- **Events**: filter by user or device; each event shows the MG code and sub-reason.
- **Settings > Identity**: Entra app registration, certificate expiry date.
