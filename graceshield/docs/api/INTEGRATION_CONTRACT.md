# Future FastAPI integration contract

> Historical planning document. Implemented API contracts are now in `API_REFERENCE.md`; database-dependent behavior still requires cloud verification.

This document proposes a boundary; no backend service has been implemented or approved.

## Products

Replace `ProductRepository` at its composition boundary with a FastAPI adapter. Suggested read endpoints: `GET /v1/products?q=&category=&min_minor=&max_minor=&sort=&page=` and `GET /v1/products/{slug}`. Return stable IDs/slugs, category IDs, image descriptions, integer `amount` with `currency: GHS`, verified availability, pagination and structured error codes. Validate responses using Zod at the adapter boundary. Distinguish network/unavailable, invalid response and not-found. Use request cancellation/timeouts, bounded retries for safe reads and customer-friendly errors. Do not expose internal response traces.

## Cart and checkout

Persist anonymous minimal IDs/quantities only. After authenticated sign-in, explicitly merge an anonymous cart through an authenticated backend mutation; validate product identity, quantity, availability and variants. Return conflicts transparently. Backend owns effective prices, discounts, stock, shipping and totals; never accept client totals as authoritative. Document merge policy and expiration before implementation. Cookie-authenticated mutations need CSRF protections and origin validation.

Checkout draft currently exists in memory only. Before connecting it, implement verified address/region eligibility and secure handling/retention of customer details. Backend must recalculate shipping, taxes (when applicable), discounts and totals. Expose only approved delivery and payment options.

## Authentication

Use an approved identity provider or backend credential system with vetted password hashing, HTTP-only Secure SameSite cookies, expiration, revocation, logout, reset and verified email. Rate-limit sensitive endpoints; check authorization and customer data isolation server-side. Never store credentials/tokens in localStorage. CustomerProfile/Address models follow an approved privacy/retention contract. No fake frontend session exists.

## Authoritative order/payment flow

1. Authenticate/authorize as appropriate and validate an idempotent order request.
2. Validate current product prices and inventory; reserve stock with transactional concurrency controls.
3. Calculate shipping/charges/totals server-side and persist authoritative order/lines.
4. Initialize payment through an approved provider using server-only secrets and a stable idempotency key.
5. Verify provider payment status server-side; never trust browser redirects.
6. Authenticate webhook signatures and timestamps; deduplicate event IDs, tolerate retries/out-of-order events.
7. Update payment/order state transactionally; prevent duplicate fulfilment with durable idempotency controls.
8. Handle pending, failed, expired, cancelled and refunded states, inventory release and retry policies.
9. Reconcile provider records with internal orders and alert on mismatches.

Future Order, OrderLine, PaymentStatus, ProductVariant and inventory reservation models need explicit state transition rules. Persist provider references rather than card details. Never collect/store card information in this frontend. Use approved hosted payment flows only after integration review. Transactional notifications and admin authorization are separate backend responsibilities.
