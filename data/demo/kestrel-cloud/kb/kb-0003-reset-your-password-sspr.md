---
id: KB-0003
title: Reset your password (self-service password reset)
doc_type: kb
system: entra
owner: Identity & Access
access: public
updated: 2026-04-16
tags: [password, sspr, account, sign-in]
---

# Reset your password

You can reset or change your Kestrel password yourself, any time, without calling the Service Desk. Your Kestrel
password is the same for your laptop sign-in, Google Workspace, MeshGate and all apps that use "Sign in with
Kestrel".

## Forgot your password

1. Go to `https://aka.ms/sspr` (or click **Forgot my password** on any Kestrel sign-in page).
2. Enter `first.last@kestrelcloud.example` and the characters shown.
3. Verify with **two** methods, for example an Authenticator notification and a code sent to your personal email.
   You set these up in KB-0001.
4. Choose a new password and confirm.

## Change your password (you know the current one)

Go to `https://mysignins.microsoft.com/security-info/password/change`, enter your current and new password.

## Password rules

- At least 14 characters. A passphrase of four or more random words is easiest to remember.
- Not one of your last 10 passwords, and not containing "Kestrel", your name or common words like "Password".
- No forced expiry. You only need to change it if you think someone knows it.

## After you reset

- **Mac:** a notification "Sign in required" appears. Click it and enter your **new** password. If asked for your
  old password, enter it to keep your keychain. If you cannot log in at the Mac login screen, use the **new**
  password; if that fails, try the old one and then follow the notification.
- **Windows:** lock your computer (Windows + L) and unlock with the new password while connected to the internet.
- **Phone:** Gmail and other apps may ask you to sign in again.
- **MeshGate:** sign out and in again if you see `MG-401`.

## Error messages

**"Your account is locked" / `AADSTS50053`**
Too many wrong attempts. Wait 15 minutes, then try again, or reset with SSPR.

**"We can't reset your password because you haven't registered"**
You have no verification methods. Contact the Service Desk; they will verify your identity and help you register.

**"Your password doesn't meet requirements"**
Check the rules above. Long passphrases work best.

## Never

- Never share your password, including with IT. The Service Desk will never ask for it.
- Never enter your password on a page that is not `login.microsoftonline.com` or a Kestrel page. If in doubt, report
  it (KB-0013).
