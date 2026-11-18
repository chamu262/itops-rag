---
id: RB-MAC-002
title: FileVault recovery key missing or invalid in Jamf
doc_type: runbook
system: jamf
owner: Endpoint Engineering
access: it-staff
updated: 2026-08-22
tags: [macos, filevault, encryption, escrow, compliance]
---

# FileVault recovery key missing or invalid in Jamf

## Purpose

Get a valid personal recovery key (PRK) escrowed to Jamf Pro for a Mac where the inventory shows
**"Individual Recovery Key Validity: Unknown / Invalid"** or no key at all. A Mac without an escrowed key fails the
endpoint baseline (CF-001) and is flagged in the weekly encryption compliance report.

## Scope

Company-owned Macs managed by Jamf Pro running macOS 14 or later.

## Prerequisites

- Jamf Pro role with "View Disk Encryption Recovery Key" privilege (Endpoint Engineering, Service Desk L2).
- The Mac is enrolled and checking in (if not, run RB-MAC-001 first).
- The configuration profile `KC-FileVault-Escrow` (FileVault Recovery Key Redirection / escrow payload) is installed.
- A user who knows their login password and has a Secure Token.

## Steps

1. Check encryption state on the Mac:
   ```bash
   fdesetup status
   sudo fdesetup list
   sudo profiles show -type configuration | grep -i -A3 FDERecoveryKeyEscrow
   ```
   You need `FileVault is On.` and the user listed in `fdesetup list`.
2. Check whether the existing key is still valid locally (prompts for the key):
   ```bash
   sudo fdesetup validaterecovery
   ```
   If the user has the old key and it returns `true`, the problem is only escrow; continue to step 3.
3. Rotate the key so a new one is generated and escrowed through the redirection profile:
   ```bash
   sudo fdesetup changerecovery -personal
   ```
   Enter the user's password when asked. The new key is written to `/var/db/FileVaultPRK.dat` and picked up at next
   inventory.
4. Submit inventory so Jamf reads the escrowed key:
   ```bash
   sudo jamf recon
   ```
5. Alternative without a terminal session: in Jamf, scope the policy **"FileVault - Reissue PRK"** (Self Service
   item, uses Jamf's reissue key workflow) to the device and ask the user to run it from Self Service. The user is
   prompted for their password at the next login.
6. If the user has no Secure Token (`sysadminctl -secureTokenStatus <user>` shows DISABLED), the key cannot be
   rotated by that user. Use the managed LAPS admin, which holds a token, to grant one:
   ```bash
   sudo sysadminctl -secureTokenOn <user> -password - -adminUser kcadmin -adminPassword -
   ```

## Verification

- Jamf record > Disk Encryption shows "Individual Recovery Key Validity: Valid" with a new escrow date.
- Smart group `FV - PRK Invalid or Missing` no longer contains the device after the next nightly recalculation.

## Rollback

Rotating the PRK invalidates the old key. That is intended. Do not decrypt the disk (`fdesetup disable`) as a
workaround; it breaks CF-001 compliance and takes hours.

## Escalation

If `changerecovery` fails with `Error: Unable to change recovery key (-69594)`, or the volume shows FileVault
"Encryption paused", escalate to Endpoint Engineering with the output of `diskutil apfs list` attached. If a user is
locked out and no key exists anywhere, it is a data-loss event: inform Security Operations before any wipe.
