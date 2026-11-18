---
id: KB-0013
title: Report a phishing email or suspicious message
doc_type: kb
system: security
owner: Security Operations
access: public
updated: 2026-08-19
tags: [phishing, security, email, report, gmail]
---

# Report a phishing email or suspicious message

If something looks wrong, report it. Reporting a real phish quickly protects your colleagues; reporting something
harmless costs nothing. You will never get in trouble for reporting.

## Signs of phishing

- Urgency or threats: "your account will be closed today", "invoice overdue".
- A sign-in link that is not `login.microsoftonline.com` or `accounts.google.com` (hover to check the real address).
- Unexpected attachments, especially `.html`, `.zip`, `.iso` or Office files asking you to "enable content".
- Requests for gift cards, bank detail changes or payments, even from a known name.
- QR codes in emails asking you to sign in ("scan to re-verify MFA").
- MFA prompts in Authenticator that you did not start.

Kestrel IT will **never** email you a link asking for your password, and never ask you to approve an MFA request.

## Report an email in Gmail (laptop)

1. Open the email. Do not click links or open attachments.
2. Click the three dots **More** (top right of the message) > **Report phishing**.
3. Confirm. The message is removed from your inbox and sent to Security Operations for review.

## Report in the Gmail app (phone)

Open the message > three dots > **Report phishing**.

## Other channels

- **Slack message, SMS or phone call**: take a screenshot and send it to `#security-report` in Slack, or email
  `security@kestrelcloud.example`.
- **Unexpected MFA prompt**: tap **Deny**, then **Report** in Authenticator. Then reset your password (KB-0003).
- **Suspicious calendar invite**: do not accept; use the three dots > **Report spam** in Calendar and post in
  `#security-report`.

## I already clicked or entered my password

Act straight away. It is not a problem to report quickly; it is a problem to wait.

1. Reset your password now (KB-0003).
2. Call the Service Desk (KB-0014) and say "I may have entered my password on a phishing page". This is handled as
   urgent at any time; out of hours the call is passed to on-call.
3. If you opened an attachment, disconnect from Wi-Fi and MeshGate and leave the laptop switched on (this helps the
   investigation).
4. Tell Security Operations what you clicked and when.

## What happens next

Security Operations reviews every report, usually within four business hours. If the same message reached others, it
is removed from all mailboxes. You get an email when your report is closed.

## Phishing simulations

Kestrel runs occasional phishing simulations. Reporting them through **Report phishing** counts as a correct report.
