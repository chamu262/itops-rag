---
id: KB-0004
title: Request software from Self Service (Mac) or Company Portal (Windows)
doc_type: kb
system: general
owner: Service Desk
access: public
updated: 2026-05-20
tags: [software, self-service, company-portal, apps, install]
---

# Request software

Most approved software can be installed yourself, without admin rights and without a ticket.

## On a Mac: Self Service

1. Open **Self Service** from Launchpad or the Dock (the Kestrel bird icon).
2. Sign in with your Kestrel account if asked.
3. Browse a category (Productivity, Development, Design, Utilities) or search, for example "Figma" or "Docker".
4. Click **Install**. Progress shows in the item; most apps take 1 to 5 minutes.

Useful Self Service items:

- **Make Me Admin (30 min)**: temporary admin rights for installs that are not in the catalogue. Use is logged.
- **Update Inventory**: sends your Mac's latest information to IT. Useful after fixing a compliance issue.
- **Storage cleanup**: removes caches and old installers.

## On Windows: Company Portal

1. Open **Company Portal** from the Start menu.
2. Go to **Apps** and search or browse.
3. Click the app, then **Install**. Watch progress in **Downloads & updates**.

If an app shows **Request**, it needs approval: your manager receives the request and the Service Desk installs it
after approval.

## Not in the catalogue?

Raise a **Software request** in the Service Desk portal `https://help.kestrelcloud.example`. Include:

- App name, version and vendor website.
- Business reason and how many people need it.
- Whether it handles customer data or needs a company account (this triggers a security review, usually 5 working
  days; see the SaaS onboarding process).

Free browser extensions and personal-licence tools also need a request. Apps with a cost need a cost-centre owner.

## Licensed apps

Some apps (for example JetBrains IDEs, Adobe Creative Cloud, Miro) need a licence seat. Request the app in Self
Service or Company Portal; the licence is assigned automatically through your group membership when you are in an
eligible team, or a request is sent to the licence owner.

## Problems

**Self Service or Company Portal is missing or empty**
Your laptop may have lost its management connection. Raise a ticket; IT will re-enrol it.

**Install stuck at "Pending" or "Downloading"**
Check you are online. On Windows, open Company Portal > **Settings > Sync**. On a Mac, run **Update Inventory** in
Self Service and try again. Restart if it is still stuck after 30 minutes.

**"Your device doesn't meet requirements"**
See KB-0010.

## Contact

Service Desk (KB-0014), Slack `#it-help`.
