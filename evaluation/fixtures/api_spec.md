# Enterprise Payment and Core API Specification

## 1. Overview
The Core Enterprise API provides financial processing, settlement, and transaction status endpoints for all business units.

## 2. Authentication and Authorization
All requests must include a valid JSON Web Token (JWT) in the HTTP Authorization header:
`Authorization: Bearer <access_token>`
Tokens are signed using asymmetric RSA keys and verified against the organization JWKS endpoint.

## 3. Rate Limits and Throttling
- Standard tier: 60 requests per minute per tenant.
- Enterprise tier: 300 requests per minute per tenant.
Exceeding the quota results in an HTTP 429 Too Many Requests response with a `Retry-After` header.

## 4. Retry Policy
For idempotent operations (GET, PUT, DELETE) and POST requests with an `Idempotency-Key` header:
- Clients should implement a maximum of 3 retries.
- Exponential backoff with jitter must be applied, starting with an initial backoff delay of 500ms.
- Maximum backoff interval between attempts must not exceed 8000ms.

## 5. Error Codes and Responses
Standard JSON error structure:
`{"error": {"code": "RESOURCE_NOT_FOUND", "message": "The requested payment ID does not exist."}}`
- HTTP 400: BAD_REQUEST
- HTTP 401: UNAUTHORIZED
- HTTP 403: FORBIDDEN
- HTTP 404: RESOURCE_NOT_FOUND
- HTTP 409: CONFLICT_DUPLICATE_TRANSACTION
- HTTP 503: SERVICE_UNAVAILABLE
