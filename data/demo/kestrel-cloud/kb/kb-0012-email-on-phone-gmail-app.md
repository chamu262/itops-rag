---
id: KB-0012
title: Kestrel email on your phone with the Gmail app
doc_type: kb
system: email
owner: Collaboration Tools
access: public
updated: 2026-04-28
tags: [email, gmail, mobile, ios, android, app-protection]
---

# Kestrel email on your phone with the Gmail app

You can read Kestrel email, calendar and Drive on your personal or company phone using Google's apps. The built-in
iPhone Mail app, Outlook for mobile with IMAP, and other third-party mail apps are **blocked** for Kestrel accounts
because they use older sign-in methods that cannot do MFA.

## iPhone

1. Install **Gmail**, **Google Calendar** and **Google Drive** from the App Store.
2. Open Gmail > **Sign in** > **Google**.
3. Enter `first.last@kestrelcloud.example`. You are redirected to the Kestrel sign-in page.
4. Sign in with your Kestrel password and approve the Authenticator request.
5. Kestrel uses Google basic mobile management on iPhone. You will not be asked to install a management profile or
   any other app.
6. Allow notifications.

## Android

1. Open **Settings > Passwords & accounts** (name varies) > **Add account** > **Google**, or open Gmail and add an
   account.
2. Enter your Kestrel email and sign in on the Kestrel page with MFA.
3. Android may ask to set up a **work profile**. Accept: Kestrel apps go in the work profile (marked with a briefcase
   icon), separate from your personal apps.

## Requirements

- A screen lock (PIN, fingerprint or face). Gmail asks you to set one if missing.
- iOS 17 or later, Android 11 or later.
- Phones that are jailbroken or rooted are blocked.

## What IT can and cannot see

IT can see the phone model, OS version and whether a screen lock is set. IT can remove the **Kestrel account** from
the phone (for example when you leave or report the phone lost). IT **cannot** see your personal email, photos,
messages or location, and cannot wipe your personal data.

## Common problems

**"Your administrator has blocked access" or error `AADSTS53003` in the browser while signing in**
You are probably using a blocked app or an old OS version. Use the Gmail app and update the phone.

**Sign-in loop on iPhone**
In Settings > Gmail make sure **Safari** cookies are not blocked for the sign-in. Delete and reinstall Gmail if it
loops again.

**No new mail notifications**
Gmail > Settings > your Kestrel account > Notifications > **All** or **High priority only**. Also check Focus modes.

**Calendar not showing in the iPhone Calendar app**
Use the Google Calendar app. Adding a Kestrel account as a CalDAV account in the iPhone Calendar app is blocked.

## Changing phone

Move Authenticator first (KB-0011), then sign in to Gmail on the new phone and remove the account from the old one.

## Lost phone

Contact the Service Desk straight away (KB-0014). They will sign out your account from the phone.
