---
id: VND-001
title: Jamf Pro - enrolment and MDM profile troubleshooting notes
doc_type: vendor
system: jamf
owner: Endpoint Engineering
access: it-staff
updated: 2026-08-04
tags: [jamf, mdm, enrolment, apns, ade, macos, notes]
---

# Jamf Pro - enrolment and MDM profile troubleshooting notes

Kestrel IT's own summary of how Jamf Pro enrolment works and where it breaks. Not vendor documentation; check the
Jamf Pro release notes for version-specific behaviour. Procedure: RB-MAC-001.

## How enrolment fits together

- **Apple Business Manager (ABM)** owns the serial-to-MDM assignment. Kestrel's MDM server in ABM is "Kestrel Jamf
  Pro"; the reseller adds new serials automatically.
- **ADE token** (server token, `.p7m`) links ABM and Jamf Pro. It expires yearly. Renewal date is tracked in the
  Endpoint Engineering calendar; expiry stops new enrolments but does not unenrol existing Macs.
- **APNs certificate** lets Jamf wake devices. Expiry stops all MDM commands for all devices. It must be **renewed**
  with the same Apple Account, never replaced with a new one, or every device must re-enrol.
- **PreStage enrolment** decides the enrolment experience. Kestrel uses `Kestrel-ADE-Standard` (mandatory, not
  removable MDM profile, account creation via Platform SSO) and `Kestrel-ADE-Kiosk` for meeting room Macs.
- **User Approved MDM** is automatic for ADE enrolments. Manual (user-initiated) enrolments need user approval and
  cannot be made non-removable.

## Health checks on a Mac

```bash
sudo profiles status -type enrollment
sudo profiles show -type enrollment
sudo jamf checkJSSConnection
sudo profiles status -type bootstraptoken
log show --predicate 'subsystem == "com.apple.ManagedClient"' --last 30m
```

## Symptoms and causes

The sections below list the symptoms we see most often in tickets, with the usual cause and fix.

## "MDM profile is not installed"

Shown in the Jamf inventory record when the device sends inventory through the `jamf` binary but the MDM profile is
gone. Causes: user removed a removable profile (older manual enrolments), Migration Assistant from another Mac,
macOS reinstall without erase. Fix: `sudo profiles renew -type enrollment` and user approval.

## "MDM Profile Expiration" date in the past

The device identity certificate in the MDM profile has a two-year life and is renewed by the Jamf "Renew MDM profile"
command. Devices offline for months may miss it. Send **Renew MDM Profile** from the record; if the device cannot
receive commands, re-enrol.

## Commands stay "Pending"

APNs cannot reach the device. Check outbound TCP 5223 and 443 to `*.push.apple.com` (office firewall rule
`FW-APNS-OUT`), and that the APNs certificate is valid in Jamf **Settings > Global > Push Certificates**.

## `profiles renew` returns "Error fetching Device Enrollment configuration"

Serial not assigned in ABM, assigned to another MDM server, or not in a PreStage scope. Also seen when the Mac has no
internet route to `iprofiles.apple.com`.

## Device enrols but shows "Unmanaged"

Jamf management account or management framework missing. Re-deploy with `sudo jamf policy -event enrollmentComplete`
or remove and re-enrol.

## Re-enrolment side effects

- Configuration profiles and Self Service apps reinstall; local data is kept.
- FileVault PRK escrow may need rotation (RB-MAC-002).
- Wi-Fi certificate is reissued (new SCEP request).
- Inventory history stays on the same computer record because the serial matches.

## Useful Jamf API calls

```bash
# Bearer token, then look up by serial
curl -su "$JAMF_CLIENT_ID:$JAMF_CLIENT_SECRET" -X POST \
  https://jamf.kestrelcloud.example/api/oauth/token -d grant_type=client_credentials
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://jamf.kestrelcloud.example/api/v1/computers-inventory?filter=hardware.serialNumber==C02XK0TESTXX"
```

## Contacts

Jamf support cases are opened by Endpoint Engineering only. Kestrel's Jamf Pro is a cloud instance; maintenance
windows are announced by the vendor and copied into `#it-status`.
