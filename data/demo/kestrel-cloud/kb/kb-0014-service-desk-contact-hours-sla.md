---
id: KB-0014
title: Contact the IT Service Desk - hours, channels and response times
doc_type: kb
system: general
owner: Service Desk
access: public
updated: 2026-09-01
tags: [service-desk, contact, sla, support-hours, priority]
---

# Contact the IT Service Desk

## Channels

| Channel | Use for |
|---|---|
| Portal `https://help.kestrelcloud.example` | Everything. Requests and problems, with attachments. Creates a ticket in project HELP. |
| Slack `#it-help` | Quick questions. A bot creates a ticket from your message if needed. |
| Email `help@kestrelcloud.example` | When you cannot reach Slack or the portal. |
| Phone `+46 8 555 010 00` (EU) / `+1 512 555 0142` (US) | Urgent problems: you cannot work at all, security incidents, lost or stolen devices. |
| Walk-up IT bar | Stockholm floor 3 and London floor 2, Tue and Thu 10:00 to 15:00 local time. |

Status of known outages is posted in `#it-status`.

## Opening hours

- **EU desk** (Stockholm, London, Lisbon): Monday to Friday, 07:00 to 19:00 CET.
- **US desk** (Austin): Monday to Friday, 08:00 to 18:00 US Central Time.
- Swedish, UK, Portuguese and US public holidays: the desk for that region is closed; the other desk covers urgent
  tickets.

**Outside these hours** only urgent problems are handled: call the phone number and your call is routed to the IT
on-call engineer. Portal and Slack tickets created out of hours are picked up the next working day.

## Priority and response times

Priority is set by the Service Desk based on impact and urgency. Times are business hours unless marked 24/7.

| Priority | Examples | First response | Target resolution |
|---|---|---|---|
| **P1 Critical** | Office or company-wide outage, security incident, suspected account compromise | 30 minutes (24/7) | 4 hours |
| **P2 High** | You cannot work: laptop broken, locked out, new joiner without a laptop on day one | 2 hours | 1 business day |
| **P3 Medium** | Something is broken but there is a workaround; one app not working | 8 business hours | 3 business days |
| **P4 Low** | Requests: new software, access to a shared drive, questions | 2 business days | 10 business days |

Requests that need approval (software with cost, access to sensitive systems) pause the clock while waiting for
the approver.

## Help us help you

Include in your ticket:

- Your device name (KB-0010 shows where to find it).
- The exact error message or code, for example `AADSTS53003`, `MG-401` or `0x80180014`, and a screenshot.
- When it started and what changed (new password, travelling, update installed).
- How many people are affected.

## Self-help first

- Password: KB-0003
- MFA and new phone: KB-0001, KB-0011
- VPN: KB-0002
- Software: KB-0004
- Compliance message: KB-0010
- Phishing: KB-0013

## Feedback

Every closed ticket has a one-question survey. Complaints or escalation about a ticket: reply to the ticket and ask
for the Service Desk lead.
