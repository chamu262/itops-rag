---
id: KB-0006
title: Wi-Fi in the office - Kestrel-Corp vs Kestrel-Guest
doc_type: kb
system: network
owner: Workplace Network
access: public
updated: 2026-02-24
tags: [wifi, network, 802.1x, certificate, guest]
---

# Wi-Fi in the office: Kestrel-Corp vs Kestrel-Guest

Every Kestrel office has two Wi-Fi networks.

| Network | Who uses it | How you join |
|---|---|---|
| **Kestrel-Corp** | Kestrel-managed laptops only | Automatically, with a device certificate (802.1X / EAP-TLS). No password. |
| **Kestrel-Guest** | Visitors, personal phones and tablets, unmanaged devices | Open network with a sign-in page; daily code shown on reception screens. |

## Kestrel-Corp

Your laptop receives a certificate from IT through Jamf (Mac) or Intune (Windows). The certificate proves the
device is a Kestrel device. You never type a password for Kestrel-Corp, and you should not be asked for one.

What Kestrel-Corp gives you:

- Access to internal systems without MeshGate.
- Office printers (KB-0005).
- Meeting room screens and Google Meet hardware (KB-0008).

### If Kestrel-Corp does not connect

1. Check your laptop is up to date and compliant (KB-0009, KB-0010). Non-compliant devices are moved to a restricted
   network.
2. **Mac:** open **System Settings > Wi-Fi**, click **...** next to Kestrel-Corp > **Forget This Network**. Then open
   Self Service > **Update Inventory** and wait 5 minutes; the network profile reinstalls.
3. **Windows:** open Company Portal > **Settings > Sync**. Then **Settings > Network & internet > Wi-Fi > Manage
   known networks**, forget Kestrel-Corp and reconnect.
4. If you are asked for a **username and password** for Kestrel-Corp, do not enter your Kestrel password. Cancel and
   raise a ticket. Your certificate is probably missing or expired.

The certificate renews automatically every year if your laptop checks in with IT regularly. Laptops that have been
switched off for more than a few months may need a ticket.

## Kestrel-Guest

- Join the network, open a browser and accept the terms with the daily code.
- Internet only. No printers, no internal systems. Use MeshGate on a Kestrel laptop if you must reach internal tools
  from Guest (KB-0002).
- Bandwidth is limited per device; large downloads are slow.
- Visitors' access expires at midnight.

## Personal phones

Use **Kestrel-Guest**. Personal devices cannot join Kestrel-Corp, even with your Kestrel account.

## Security notes

- Never share the Kestrel-Corp certificate or try to export it.
- If you see a network named similar to ours (for example "Kestrel-Corp-Free" or "KestrelCorp"), do not join it and
  report it to the Service Desk.

## Contact

Service Desk (KB-0014). For a whole floor without Wi-Fi, post in `#it-help` so the network team sees it quickly.
