# Demo corpus: Kestrel Cloud (fictional)

Everything in this folder is **made up**. Kestrel Cloud is a fictional B2B SaaS company with about 800 staff in four
offices (Stockholm, London, Austin, Lisbon). No real company, person, tenant, hostname or ticket is described here.
All domains use the reserved `.example` TLD (`kestrelcloud.example`), all IPs come from documentation ranges
(`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) or RFC 1918 space, and all "secrets" are obviously fake.

The corpus exists to exercise every loader, the redaction step, access tags, prompt-injection handling and the eval set.

## Layout

| Folder | Format | Loader | What it holds |
|---|---|---|---|
| `kestrel-cloud/runbooks/` | Markdown + front matter | `markdown` | Step-by-step operational procedures |
| `kestrel-cloud/kb/` | Markdown + front matter | `markdown` | Help desk KB articles (end-user facing) |
| `kestrel-cloud/vendor/` | PDF (built from `sources/vendor/*.md`) | `pdf` | Vendor-style admin notes for MDM, identity, VPN |
| `kestrel-cloud/confluence/` | Confluence-style HTML export | `confluence_html` | IT space pages: standards, architecture, onboarding |
| `kestrel-cloud/tickets/` | `tickets.csv` (Jira-style) + `servicedesk.json` (ServiceNow-style) | `tickets` | Resolved help desk tickets |
| `kestrel-cloud/changes/` | YAML | `records` | CAB change records |
| `kestrel-cloud/incidents/` | Markdown + front matter | `markdown` | Blameless post-mortems |
| `kestrel-cloud/oncall/` | Markdown + front matter | `markdown` | On-call Q&A, handover notes, escalation matrix |
| `kestrel-cloud/adversarial/` | Markdown | `markdown` | Prompt-injection and secret-leak test docs |

## Front matter (Markdown docs)

```yaml
---
id: RB-MAC-003            # stable, unique; prefixes: RB runbook, KB, VND vendor, CF confluence, PM post-mortem, OC on-call, ADV adversarial
title: Re-enrol a Mac that dropped out of Jamf
doc_type: runbook         # runbook | kb | vendor | standard | postmortem | oncall | change | ticket
system: jamf              # jamf | intune | entra | gws | meshgate | macos | windows | network | email | saas | security | general
owner: Endpoint Engineering   # a TEAM name, never a person
access: it-staff          # public | it-staff | security
updated: 2026-09-14
tags: [macos, mdm, enrolment]
---
```

## Access tags

- `public`: anyone in the company (help desk L1, end-user facing KB).
- `it-staff`: IT engineers and on-call.
- `security`: security team only (incident details, break-glass procedures).

A caller with role `it-staff` sees `public` + `it-staff`; `security` sees all three; `public` sees only `public`.

## Teams (use these as owners)

Endpoint Engineering · Identity & Access · Workplace Network · Collaboration Tools · Service Desk · Security Operations ·
Platform SRE

## Systems in the fictional estate

- Macs (~520) managed by **Jamf Pro**; Windows (~260) managed by **Microsoft Intune**; iPhones/iPads via Jamf.
- Identity: **Microsoft Entra ID** is the IdP (SSO via SAML/OIDC to SaaS apps); **Google Workspace** for mail,
  calendar and Drive, federated from Entra.
- Remote access: a WireGuard-based mesh VPN called **"MeshGate"** (fictional product) plus Entra Conditional Access.
- Patching: Jamf patch policies for macOS, Intune update rings for Windows.
- Ticketing: help desk project key `HELP`, change key `CHG`, incidents `INC`.

## Fake PII (for redaction tests)

Tickets deliberately contain fake names, `firstname.lastname@kestrelcloud.example` addresses, phone numbers like
`+46 70 123 45 67` / `+44 7700 900123`, serial numbers and a few fake tokens. The ingest step must mask them; the
redaction report in `eval/` shows what was masked.
