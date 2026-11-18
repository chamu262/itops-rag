---
id: KB-0010
title: '"Your device is not compliant" message'
doc_type: kb
system: intune
owner: Endpoint Engineering
access: public
updated: 2026-10-14
tags: [compliance, conditional-access, intune, jamf, sign-in]
---

# "Your device is not compliant" message

Kestrel only allows company data on devices that meet our security baseline. If your laptop falls below it, you
see a message like one of these:

- "Your device is required to be compliant to access this resource"
- "You can't get there from here" with error code **`AADSTS53000`**
- "Device not compliant" or "Check access" in Company Portal
- MeshGate error `MG-301`

You can usually fix it yourself in a few minutes.

## Windows: what to do

1. Open **Company Portal** > **Devices** > your device. It lists what is wrong, for example "Encryption required" or
   "Update OS version".
2. Fix each item:
   - **OS version**: Start > **Settings > Windows Update > Check for updates**, install and restart.
   - **Defender / antivirus**: open **Windows Security** and make sure real-time protection is on.
   - **Encryption (BitLocker)**: restart once while connected to the internet; IT turns it on automatically.
3. In Company Portal click **Check access** (or **Settings > Sync**). It can take up to 15 minutes to update.
4. Close and reopen the app or browser that showed the message.

## Mac: what to do

1. Open **Self Service**. A banner shows any compliance issue.
2. Common fixes:
   - **macOS out of date**: follow KB-0009.
   - **FileVault off**: open **System Settings > Privacy & Security > FileVault** and check it is on. If it is on and
     you still get the message, raise a ticket.
   - **Device not checked in**: in Self Service run **Update Inventory**.
3. Wait 15 minutes and try again.

## Why can't I just be excluded?

The rule protects customer data if a laptop is lost or attacked. IT can give a short temporary exception (at most
three days) while a fix is in progress, but only with a ticket.

## "Not evaluated" or "Checking compliance" for hours

This usually means your device has not talked to IT's management service for a while, for example after a long
holiday. Make sure you are online, restart, and sync as above. If it still says "Not evaluated" after an hour, raise a
ticket.

## Personal devices

Personal laptops cannot become compliant; they are not enrolled in Kestrel management. Use a Kestrel laptop, or use
Google Workspace in the browser where allowed. On personal phones, use the Gmail app as described in KB-0012.

## Raising a ticket

Include:

- Device name (Windows: Settings > System > About; Mac: Self Service > "Device info"), for example
  `KC-LON-WL-03311` or `KC-STO-MBP-04217`.
- The exact message and error code, and a screenshot.
- What you have already tried.

Service Desk details: KB-0014.
