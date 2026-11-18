---
id: RB-WIN-003
title: Retrieve a BitLocker recovery key
doc_type: runbook
system: intune
owner: Endpoint Engineering
access: it-staff
updated: 2026-06-18
tags: [windows, bitlocker, recovery, encryption, entra]
---

# Retrieve a BitLocker recovery key

## Purpose

Give a user their 48-digit BitLocker recovery key when the device boots to the blue **"BitLocker recovery"** screen,
safely and with an audit trail.

## Scope

Kestrel Windows devices joined to Entra and managed by Intune. Keys are escrowed to Entra ID at encryption time by
the `ES-Win-BitLocker` endpoint security policy.

## Prerequisites

- Role with `microsoft.directory/bitlockerKeys/key/read` (Kestrel custom role **KC BitLocker Key Reader**, held by
  Service Desk L2 and Endpoint Engineering). Every read is logged in Entra audit logs.
- The **Recovery key ID** shown on the user's screen (first 8 characters are enough).

## Steps

1. Verify the caller's identity. Call them back on the number in the HR system or verify on a video call with their
   badge. Never read a key to someone calling from an unknown number or replying to an email.
2. Get the key ID from the user's recovery screen, for example `3A7F21C0`.
3. Retrieve in the portal: Intune > **Devices > Windows > (device) > Recovery keys**, or Entra admin center >
   **Devices > BitLocker keys**, search by key ID. Click **Show recovery key**.
4. Or with Microsoft Graph:
   ```powershell
   Connect-MgGraph -Scopes BitLockerKey.Read.All
   Get-MgInformationProtectionBitlockerRecoveryKey -Filter "deviceId eq '<deviceId>'"
   Get-MgInformationProtectionBitlockerRecoveryKey -BitlockerRecoveryKeyId <keyId> -Property key
   ```
5. Read the key in groups of six digits. Do not paste it in Slack or the ticket.
6. Note in the HELP ticket: device name, key ID and reason. Not the key.
7. After the user is in, rotate the key from Intune: device > **...> BitLocker key rotation**. The new key is escrowed
   automatically.

## If no key is found

- Check the device's other objects: a reimaged device may have keys under an older device ID.
- On a working device you can confirm local protectors with `manage-bde -protectors -get C:` and force escrow:
  ```powershell
  $kp = (Get-BitLockerVolume -MountPoint C:).KeyProtector | Where-Object KeyProtectorType -eq RecoveryPassword
  BackupToAAD-BitLockerKeyProtector -MountPoint C: -KeyProtectorId $kp.KeyProtectorId
  ```
- If no key exists anywhere, the data cannot be recovered. Tell the user, reimage via Autopilot (RB-WIN-001) and
  inform Security Operations because it means the escrow control failed.

## Common causes of recovery prompts

Firmware or BIOS update without suspending BitLocker, docking station boot order change, TPM cleared, Secure Boot
changes. Repeated prompts on the same model: check OC-005.

## Verification

User reaches the desktop; Intune shows a new key with today's date after rotation.

## Rollback

Not applicable.

## Escalation

Endpoint Engineering. Requests from managers or third parties to obtain a key for another user's device go to
Security Operations.
