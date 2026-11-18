---
id: KB-0002
title: Connect to the MeshGate VPN
doc_type: kb
system: meshgate
owner: Workplace Network
access: public
updated: 2026-10-01
tags: [vpn, meshgate, remote-work, travel]
---

# Connect to the MeshGate VPN

MeshGate is Kestrel's VPN. You need it when working outside a Kestrel office to reach internal tools such as the
intranet, build systems and admin consoles. Google Workspace, Slack and most SaaS apps work **without** MeshGate.

## Install

MeshGate is installed automatically on Kestrel laptops. If you do not see it:

- **Mac:** open **Self Service**, search "MeshGate", click **Install**.
- **Windows:** open **Company Portal**, search "MeshGate", click **Install**.

See KB-0004 if Self Service or Company Portal is missing.

## Connect

1. Click the MeshGate icon in the menu bar (Mac) or system tray (Windows).
2. Click **Sign in**. Your browser opens the Kestrel sign-in page. Sign in and approve the Authenticator request.
3. Return to MeshGate and click **Connect**. The icon turns green and shows the nearest gateway, for example
   "Stockholm" or "Austin".

MeshGate stays signed in for 12 hours. After that you will be asked to sign in again.

## Choosing a gateway

MeshGate picks the fastest gateway automatically. If a colleague in IT asks you to, you can choose one manually under
**Settings > Gateway**: Stockholm, London, Austin or Lisbon.

## Error messages

| Message | What to do |
|---|---|
| `MG-401` Sign-in failed or expired | Click **Sign out**, then **Sign in** again. If you recently changed your password, make sure your laptop is using the new one. |
| `MG-403` You do not have access | You are not in the MeshGate user group. Contact the Service Desk. New joiners get access within two hours of their start time. |
| `MG-301` Device check failed | Your laptop is not compliant. See KB-0010. |
| `MG-302` Update required | Your operating system is too old. Mac: see KB-0009. Windows: run Windows Update and restart. |
| `MG-201` Cannot reach gateway | The network you are on may block VPN traffic (common on hotel and airport Wi-Fi). Wait 30 seconds; MeshGate tries another method automatically. If it still fails, try a phone hotspot. |
| `MG-503` Service unavailable | The gateway is temporarily unavailable. Try **Settings > Gateway** and choose another office. If all fail, check `#it-status` in Slack. |

## Tips

- In the office you do not need MeshGate; the office network gives the same access.
- Hotel captive portals: open a browser and accept the hotel terms **before** connecting MeshGate.
- Travelling outside Europe, the UK and the US? Some countries are blocked for sign-in. Contact the Service Desk at
  least five working days before you travel.

## Still stuck?

Click **Help > Create diagnostics** in MeshGate. It saves a file to your Desktop. Raise a ticket with the Service
Desk (KB-0014) and attach the file.
