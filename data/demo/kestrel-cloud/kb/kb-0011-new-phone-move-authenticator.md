---
id: KB-0011
title: New phone - move Microsoft Authenticator
doc_type: kb
system: entra
owner: Identity & Access
access: public
updated: 2026-06-02
tags: [mfa, authenticator, new-phone, migration]
---

# New phone: move Microsoft Authenticator

Do this **before** you reset, trade in or give away your old phone. Moving Authenticator yourself takes 10 minutes.
Without the old phone, you will need the Service Desk to verify your identity and reset your MFA.

## Option 1: you still have the old phone (recommended)

1. On your **new** phone install **Microsoft Authenticator**.
2. On your Kestrel laptop open `https://aka.ms/mysecurityinfo` and sign in. Approve the request on your **old**
   phone.
3. Click **+ Add sign-in method** > **Microsoft Authenticator** and follow the steps to scan the QR code with the
   **new** phone (same as KB-0001).
4. Approve the test notification on the new phone.
5. Back on the Security info page, set **Default sign-in method** to "Microsoft Authenticator - notification" on the
   new phone if asked.
6. Find the old phone in the list and click **Delete**.
7. On the old phone, remove the Kestrel account from Authenticator (tap the account > settings gear > **Remove
   account**).

## Option 2: backup and restore

If you turned on **Backup** in Authenticator (iCloud on iPhone, Google account on Android):

1. Install Authenticator on the new phone and sign in to the same iCloud / Google account.
2. Tap **Begin recovery**.
3. Your Kestrel account appears with "Action required". Tap it and sign in. Work accounts always need you to sign in
   again after a restore; that is normal.

Restore does not work between iPhone and Android. Use option 1 when switching platforms.

## Option 3: old phone lost, broken or already reset

1. Contact the Service Desk (KB-0014) by phone or from a colleague's laptop in `#it-help`.
2. They verify your identity on a video call (have your badge or ID ready).
3. They remove the old phone and give you a one-time **Temporary Access Pass**, valid for one hour.
4. Use it at `https://aka.ms/mysecurityinfo` to register Authenticator on the new phone (KB-0001).

If the old phone was lost or stolen and had Gmail or Slack on it, tell the Service Desk so they can sign it out
remotely.

## After moving

- Check you can sign in to Gmail on your laptop and approve the request on the new phone.
- If you use **phone sign-in** (passwordless), enable it again on the new phone.
- Gmail app and other work apps on the new phone: KB-0012.

## Tips

- The Service Desk will never ask you to approve a request or read out a number. If someone does, deny and report it
  (KB-0013).
- Keep Authenticator backup turned on.
