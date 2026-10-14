# Enterprise Security and Data Protection Policy

## 1. Tenant Isolation & Row-Level Security
Multi-tenant data isolation is enforced at the database layer using PostgreSQL Row-Level Security (RLS). Every table containing user data (`documents`, `document_chunks`, `feedback`) has RLS enabled with a default deny posture.
The backend API derives `owner_id` exclusively from verified JWT cryptographic claims and never trusts client form inputs.

## 2. Password and Credential Standards
- User passwords must have a minimum length of 12 characters.
- Must contain at least one uppercase letter, one lowercase letter, one number, and one special symbol.
- Accounts are locked for 30 minutes following 5 consecutive failed login attempts.

## 3. Session Management and Timeouts
- User authentication sessions expire after 15 minutes of user inactivity.
- Refresh tokens are valid for up to 7 days and must be revoked immediately upon sign-out.

## 4. Audit Logging and Retention
- All administrative actions, authentication attempts, document uploads, and document deletions are recorded in the central audit ledger.
- Audit logs must be retained for a mandatory minimum period of 365 days.
- Audit records must never contain customer secrets, authentication passwords, or unredacted document payloads.

## 5. Indirect Prompt Injection Safeguards
All uploaded documents and external data are marked as untrusted reference context. The LLM system prompt mandates that instructions inside user files cannot alter system operational rules or call unauthorized tools.
