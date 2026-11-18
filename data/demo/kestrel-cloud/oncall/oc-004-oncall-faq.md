---
id: OC-004
title: IT on-call FAQ
doc_type: oncall
system: general
owner: Platform SRE
access: it-staff
updated: 2026-11-02
tags: [oncall, faq, paging, escalation]
---

# IT on-call FAQ

Short answers to the questions new on-call engineers ask most. Rules: CF-005. Who to call: OC-001.

**1. A user messages me directly on Slack at 22:00 saying they cannot sign in. Do I help?**
Slack DMs are not pages. Ask them to call the Service Desk number (KB-0014) so the request is logged and routed. If it
is clearly a single-user issue (SEV4), it waits for the morning unless they are an urgent leaver case or a security
issue.

**2. What counts as urgent out of hours for a single user?**
Suspected account compromise, lost or stolen device (RB-SEC-001), urgent leaver from HR (RB-GEN-002), and executives
travelling with a blocking issue. Everything else is next business day.

**3. A user is locked out with `AADSTS53003` while abroad. Can I add them to a travel exception?**
Only with manager approval in the ticket, and only via the `SG-CA-Travel-<ISO>` group with an end date. Never exclude
them from the policy directly. Procedure: RB-IDM-002. Suggest MeshGate first; gateway IPs are a trusted location.

**4. Can I reset MFA for someone at night?**
Yes, after identity verification on video with ID (RB-IDM-001). If you cannot verify, do not reset. Social engineering
of on-call is a known attack pattern; call Security Operations if in doubt.

**5. I got paged for a MeshGate gateway alert but users are not complaining. Is it still SEV2?**
One gateway down with automatic failover working is SEV3 out of hours; drain the gateway, confirm failover and leave a
note for Workplace Network. It becomes SEV2 if a second gateway degrades or failover does not happen.

**6. How do I get admin rights during an incident?**
Activate your eligible roles in PIM (Entra admin center > Identity Governance > Privileged Identity Management > My
roles). Activation needs a justification; put the INC number. Do not use break-glass accounts.

**7. A Mac shows "MDM profile is not installed" and the user cannot reach Self Service. Do I fix it now?**
No, unless it blocks a SEV1/SEV2. Leave it for Endpoint Engineering with RB-MAC-001 linked. Many devices at once is
different: check the APNs certificate (VND-001).

**8. Who decides to wipe a stolen laptop at night?**
The on-call can lock immediately. Wipe follows RB-SEC-001 rules (stolen = wipe). Security Operations on-call should be
informed for any theft.

**9. The change calendar shows a CHG tonight. Do I need to be involved?**
Only if the change owner asked for on-call support in the CHG record. You should know it is happening (listed in the
handover, OC-002) so you can connect alerts to it.

**10. I can't reach the owning team's L2 and the L3 is not answering either.**
Page the IT Operations manager via the paging tool, then keep working the incident as IC. Record the escalation
attempts in the INC timeline.

**11. Can I swap a shift at short notice?**
Yes. Agree in `#it-oncall`, then the person giving away the shift updates the paging schedule. You are on call until
the schedule shows otherwise.

**12. I was paged three times last night. Do I still start at 08:00?**
No. Tell your lead and start later; the rota rules allow rest after night pages. Log the hours for compensation.
