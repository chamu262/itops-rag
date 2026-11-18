---
id: KB-0001
title: Set up MFA with Microsoft Authenticator
doc_type: kb
system: entra
owner: Identity & Access
access: public
updated: 2026-06-02
tags: [mfa, authenticator, sign-in, security-info]
---

# Set up MFA with Microsoft Authenticator

Every Kestrel account must use multi-factor authentication (MFA). We use the **Microsoft Authenticator** app with
number matching. SMS codes are not allowed for Kestrel accounts.

## What you need

- Your computer, signed in or able to sign in to your Kestrel account (on day one you get a Temporary Access Pass from
  the Service Desk).
- An iPhone (iOS 17 or later) or Android phone (Android 10 or later). This can be your own phone. Installing
  Authenticator does not give IT any control over your phone.

## Steps

1. On your phone, install **Microsoft Authenticator** from the App Store or Google Play. Check the publisher is
   Microsoft Corporation.
2. On your computer, open `https://aka.ms/mysecurityinfo` and sign in with `first.last@kestrelcloud.example`.
3. Click **+ Add sign-in method**, choose **Microsoft Authenticator**, then **Next** until a QR code appears.
4. In the app, tap **+** > **Work or school account** > **Scan QR code** and scan the code on your screen.
5. Allow notifications when the app asks. Without notifications you will not see sign-in requests.
6. Back on the computer, click **Next**. A test notification is sent. Type the two-digit number shown on your
   computer into the app and approve.
7. Recommended: in the app, open your Kestrel account and tap **Enable phone sign-in** so you can sign in without a
   password on your phone.

## Good habits

- Only approve a request if **you** just tried to sign in and the number matches. If you get a request you did not
  start, tap **Deny**, then choose **Report** and tell the Service Desk. Someone may have your password; reset it
  (KB-0003).
- Turn on app lock (Face ID / fingerprint) in Authenticator settings.
- Turn on **Backup** in Authenticator settings (iCloud or Google account). This makes moving to a new phone easier
  (KB-0011).

## Common problems

**"Your sign-in was blocked" / "You can't get there from here" while registering**
You can only add security info from a Kestrel-managed device or with a Temporary Access Pass. Use your work laptop.

**No notification arrives**
Open the Authenticator app directly; pending requests appear there. Check the phone has internet and that Focus /
Do Not Disturb is not blocking Authenticator.

**Error message with `AADSTS50076` or "Additional verification required" but no prompt**
Your registered method may be on an old phone. Contact the Service Desk; after an identity check they can reset your
methods.

**I got a new phone**
See KB-0011.

## Need help?

Contact the Service Desk (KB-0014). The Service Desk will never ask you to read out an MFA number or approve a request
on their behalf.
