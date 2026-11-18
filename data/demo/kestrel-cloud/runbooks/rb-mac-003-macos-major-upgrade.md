---
id: RB-MAC-003
title: macOS major upgrade deferral and forced upgrade
doc_type: runbook
system: macos
owner: Endpoint Engineering
access: it-staff
updated: 2026-09-30
tags: [macos, patching, softwareupdate, ddm, deferral]
---

# macOS major upgrade deferral and forced upgrade

## Purpose

Control when Kestrel Macs move to a new major macOS release: hold it back while apps are certified, then enforce the
upgrade by a deadline. Policy and SLAs are in CF-004 (Patching policy).

## Scope

All Jamf-managed Macs. The macOS 26 to macOS 27 cycle (autumn 2026) is the current example.

## Prerequisites

- Jamf Pro admin rights for configuration profiles and Managed Software Updates (Declarative Device Management).
- App compatibility sign-off recorded on the change ticket (CHG) by Endpoint Engineering and app owners.
- Bootstrap token escrowed on target Macs (`sudo profiles status -type bootstraptoken`), otherwise silent installs
  fail on Apple silicon.

## Steps: deferral (release day)

1. Confirm the restrictions profile `KC-macOS-Major-Deferral` is scoped to `All Managed Macs` with:
   - `forceDelayedMajorSoftwareUpdates = true`
   - `enforcedSoftwareUpdateMajorOSDeferredInstallDelay = 60` (days, max 90)
2. Exclude the pilot group `SG-Mac-Pilot` (IT and volunteers, about 40 Macs) so they see the upgrade immediately.
3. On a pilot Mac verify the deferral is effective for others:
   ```bash
   softwareupdate --list --include-config-data
   sudo profiles show -type configuration | grep -i Deferred
   ```

## Steps: forced upgrade (after sign-off)

1. Reduce the deferral to 0 or remove `KC-macOS-Major-Deferral` from scope for the target wave.
2. In Jamf: **Computers > Managed Software Updates > New Plan**. Choose the wave smart group (`Wave 1 - Stockholm and
   Lisbon`, `Wave 2 - London`, `Wave 3 - Austin`), action "Download and install", the target version (for example
   `27.0.1`) and a local deadline 14 days out, 17:00.
3. DDM handles reminders: notifications grow more frequent in the last 24 hours and the Mac restarts at the deadline
   with a 60-minute warning.
4. Announce each wave in `#it-announcements` and link KB-0009.
5. Track progress with the smart group `macOS < 27` and the Managed Software Update plan status. Expected states are
   `Downloading`, `Scheduled`, `Installing`, `Succeeded`.

## Verification

```bash
sw_vers -productVersion
```
Jamf inventory "Operating System Version" matches the target within one recon cycle. Plan status shows "Succeeded".

## Troubleshooting

- Plan stuck at `Downloading` on a few Macs: free disk below 25 GB. Ask the user to clear space, or run the
  "Storage cleanup" Self Service item.
- Error `Failed to authorize the update` / `MDMClientError 72`: bootstrap token missing. Fix as in RB-MAC-001 step 6.
- Users on MeshGate overseas with slow links: allow download over 7 days before setting the deadline.

## Rollback

Apple does not support downgrading macOS. Rollback means pausing: delete the plan for remaining waves and re-scope
`KC-macOS-Major-Deferral`. A Mac that is broken after upgrade gets a loaner while Endpoint Engineering reimages it.

## Escalation

Endpoint Engineering (component "macOS updates"). An app blocker found after a wave started: raise with the app owner
and Endpoint Engineering lead; see the known-issues list OC-005.
