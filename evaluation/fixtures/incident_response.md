# Enterprise Incident Response and Escalation Runbook

## 1. Severity Classifications
- Severity 1 (Critical): Total outage of payment processing or data compromise. Response SLA: 15 minutes.
- Severity 2 (Major): Partial service impairment or performance degradation affecting multiple tenants. Response SLA: 60 minutes.
- Severity 3 (Minor): Non-critical bugs, cosmetic issues, or single-user inconvenience. Response SLA: 24 business hours.

## 2. On-Call Escalation Procedures
The primary on-call engineer is paged automatically via the alert gateway. If no acknowledgement is received within 10 minutes, the incident escalates to the secondary on-call engineer and engineering manager.

## 3. Post-Incident Reviews (PIR)
For all Severity 1 and Severity 2 incidents:
- A blameless retrospective meeting must be held within 72 hours of incident resolution.
- The incident commander must publish an action item report detailing root cause analysis and preventative guardrails.
