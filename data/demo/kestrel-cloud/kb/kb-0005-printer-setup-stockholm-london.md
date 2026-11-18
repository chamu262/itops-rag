---
id: KB-0005
title: Set up printing in the Stockholm and London offices
doc_type: kb
system: network
owner: Workplace Network
access: public
updated: 2026-03-11
tags: [printing, printers, stockholm, london, office]
---

# Set up printing in the Stockholm and London offices

Kestrel uses **follow-me printing**: you send a job to one shared queue, then release it at any printer by tapping
your office badge. Jobs not released within 24 hours are deleted.

## Install the print queue

The queue is installed automatically on Kestrel laptops when you first connect to `Kestrel-Corp` Wi-Fi in an office.
If you do not see it:

- **Mac:** Self Service > search "Printing - Stockholm" or "Printing - London" > **Install**.
- **Windows:** Company Portal > "Kestrel Follow-Me Printing (STO)" or "(LON)" > **Install**.

The queue names are:

| Office | Queue | Printers |
|---|---|---|
| Stockholm | `KC-STO-FollowMe` | `KC-STO-PRN-301` (floor 3, by the kitchen), `KC-STO-PRN-501` (floor 5, open area), `KC-STO-PRN-502` (floor 5, colour A3) |
| London | `KC-LON-FollowMe` | `KC-LON-PRN-201` (floor 2, reception side), `KC-LON-PRN-401` (floor 4, colour) |

Printing only works on `Kestrel-Corp` Wi-Fi or office ethernet. It does not work from `Kestrel-Guest` or over
MeshGate from home.

## Print and release

1. Print from any app and choose the follow-me queue for your office.
2. Go to any printer in that office.
3. Tap your badge on the reader. The first time, the printer asks you to sign in with your Kestrel email and a PIN
   sent to you; after that, the badge is linked.
4. Select your jobs and press **Print**, or **Print all**.

## Defaults

- Black and white, double-sided. Change this in the print dialog if you need colour.
- A4 paper. A3 is available on `KC-STO-PRN-502` only.

## Scanning

At the printer, choose **Scan to me**. The scan is emailed to your Kestrel address as a PDF. Scanning to USB is
disabled.

## Problems

**Job does not appear at the printer**
Check you were on `Kestrel-Corp` when printing. Open the print queue on your laptop; if the job shows an error,
delete it, remove the queue and reinstall from Self Service / Company Portal.

**Badge not recognised**
Sign in with email and PIN at the printer, then choose **Link badge**. New badges take up to one hour to sync.

**Paper jam, toner or hardware fault**
Stockholm: report to reception. London: report to the office team. Then raise a ticket including the printer name on
the label (for example `KC-LON-PRN-401`).

**Austin and Lisbon offices**
These offices use the same system; queue names are `KC-AUS-FollowMe` and `KC-LIS-FollowMe`. Ask the local office
team for printer locations.

## Contact

Service Desk (KB-0014).
