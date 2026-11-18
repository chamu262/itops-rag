---
id: PM-2026-04
title: GitHub personal access token committed to a public repository
doc_type: postmortem
system: security
owner: Security Operations
access: security
updated: 2026-06-02
tags: [security, secrets, github, token, leak, revocation]
---

# PM-2026-04: GitHub personal access token committed to a public repository

Blameless post-mortem. Related: INC0010004, HELP-1052. Access restricted to Security Operations.

## Summary

On 2026-05-26 at 09:12 UTC, secret scanning flagged a GitHub personal access token (classic) in a commit to a
public demo repository in the Kestrel Cloud GitHub organisation. The token had `repo` and `read:org` scopes. An
engineer had copied it into a `.env.example` file while debugging a deployment script. The token was revoked
18 minutes after the alert. The audit log showed no use from outside known Kestrel IP ranges. The next day the
same token was also found pasted in a Google Doc (HELP-1052), but it had already been revoked.

Token as recorded in the alert (fake, for the record only): `ghp_FAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKE1234`.

## Impact

- For 41 minutes (commit at 08:49, revoked at 09:30), the token was publicly readable. It allowed read and
  write access to the private repositories that the owning engineer could access.
- No evidence of misuse. All API calls with the token in the audit log came from the engineer's own MeshGate
  egress IP (203.0.113.60) or office ranges.
- No customer data was in scope of the token.

## Timeline (UTC)

| Time | Event |
|---|---|
| 2026-05-26 08:49 | A commit containing the token is pushed to a public repository. |
| 09:12 | A secret scanning alert reaches Security Operations. |
| 09:20 | The token owner is identified from the token metadata and contacted by phone. |
| 09:30 | The owner revokes the token. Security Operations confirms the revocation in the org's PAT list. |
| 09:45 | The repository is made private during clean-up. |
| 10:30 | History is rewritten to remove the file, and a cache purge is requested from GitHub support. |
| 11:00 | The audit log review is complete with no suspicious use. |
| 12:40 | The incident is resolved. |
| 2026-05-27 14:00 | The same token is found in a shared Google Doc (HELP-1052). It is already revoked, and the doc history is purged. |

## Root cause

Engineers could create classic PATs with broad scopes and no expiry, and push protection was off for the
organisation. The deployment script read the token from a local `.env` file, and the engineer copied that file
to `.env.example` as a template without removing the value. No pre-commit secret check ran locally.

## What went well

- Secret scanning alerted within 23 minutes of the push.
- The owner was easy to reach and revoked the token quickly.
- Audit logs gave clear evidence that the token was not misused.

## What went wrong

- Classic PATs with no expiry were allowed.
- Push protection was not enabled, so the commit was not blocked.
- The token also existed in a shared document, which shows tokens were being shared by copy and paste.

## Action items

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Enable push protection for secret scanning org-wide. | Security Operations | Done |
| 2 | Block classic PATs at the org level; require fine-grained PATs with a maximum 90-day lifetime and admin approval. | Security Operations | Done |
| 3 | Move deployment automation to a GitHub App or OIDC federation instead of user tokens. | Platform SRE | In progress |
| 4 | Add a pre-commit secret scanning hook to the engineering laptop baseline (Jamf and Intune). | Endpoint Engineering | Done |
| 5 | Add a DLP rule in Google Workspace that warns on token-like strings in Docs. | Collaboration Tools | In progress |
| 6 | Run a short awareness session on secret handling for engineering teams. | Security Operations | Done |
