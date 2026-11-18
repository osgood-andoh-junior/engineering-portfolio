# API reference

All commerce endpoints use `/api/v1`. FastAPI publishes OpenAPI at `/openapi.json` and interactive docs at `/docs`. Pydantic request contracts reject unexpected fields and validate quantities/IDs/prices/SKUs/slugs/images. Zod validates frontend responses. Error envelope: `{ "error": { "code": "...", "message": "...", "requestId": "..." } }`; validation errors omit raw inputs to avoid echoing credentials.

## Authentication and customer sessions

| Method/path                       | Behavior                                                                         |
| --------------------------------- | -------------------------------------------------------------------------------- |
| GET `/auth/session`               | Create/restore anonymous session, set HTTP-only cookie, return CSRF token        |
| POST `/auth/register`             | Register customer profile; no role assignment; no fabricated email delivery      |
| POST `/auth/login`                | Verify Argon2id password, rotate session and merge guest cart                    |
| POST `/auth/logout`               | Invalidate current session and cookie                                            |
| GET `/auth/me`                    | Return current user’s safe profile/roles; never password/session hashes          |
| POST `/auth/verification/request` | Authenticated, rate-limited, configured email gateway required                   |
| POST `/auth/verification/confirm` | Consume expiring one-use verification token                                      |
| POST `/auth/password/request`     | Generic eligible-account response; explicit unavailable status if email disabled |
| POST `/auth/password/confirm`     | Consume reset token, change hash and invalidate all sessions                     |

Cookie-authenticated mutations require `X-CSRF-Token` from `/auth/session` plus an exact allowed `Origin`. Browser calls stay same-origin through Next rewrites; CORS is allowlisted. Session/identity traffic uses `Cache-Control: no-store`.

## Catalogue and shopping

| Method/path                                | Behavior                                                                                                                                            |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| GET `/categories`, `/categories/{slug}`    | Non-archived categories                                                                                                                             |
| GET `/products`                            | Published products in active categories; `q`, `category` UUID, `min_minor`, `max_minor`, `sort` (`price-asc`, `price-desc`, `name`), `page`; 8/page |
| GET `/products/{slug}`                     | Product, validated images/options/availability; missing/unpublished 404                                                                             |
| GET `/cart`                                | Current guest/customer bag with current backend prices and per-line validity                                                                        |
| POST `/cart/items`                         | Add `{variant_id, quantity}` after availability validation                                                                                          |
| PUT `/cart/items/{variant_id}`             | Set validated quantity; body ID must match route                                                                                                    |
| DELETE `/cart/items/{variant_id}`, `/cart` | Remove one line / clear bag                                                                                                                         |
| POST `/checkout/prepare`                   | Verified customer, address/contact body and `Idempotency-Key`; transactional server totals/reservation/pending order                                |
| GET `/orders`, `/orders/{uuid}`            | Owner-only order snapshots, 20/page                                                                                                                 |
| POST `/orders/{uuid}/cancel`               | Owner-only permitted cancellation; release pending reservation                                                                                      |

Checkout body fields: `firstName`, `lastName`, `email`, `phone`, `address`, `region`, `city`. Client totals/stock/roles/payment status are not accepted. GHS money uses integer pesewas. Idempotency keys are scoped per customer; retries with different checkout details return conflict. A prepared order is pending payment, not a successful payment. Reservation expiry is returned explicitly.

## Administration

Every `/admin` route requires an active verified admin session, with CSRF on mutations. Audit events record actor/action/resource. No frontend-only access decision is trusted.

- GET `/admin/overview`: real stored record counts, low-stock count, verified-paid lifecycle sales sum; no invented analytics.
- GET/POST `/admin/categories`; PUT/DELETE `/admin/categories/{uuid}` (archive, hierarchy-cycle validation).
- GET/POST `/admin/products`; PUT/DELETE `/admin/products/{uuid}`; POST `/admin/products/{uuid}/variants`. Prices in integer pesewas. Product update currently edits the first variant’s SKU and replaces the image collection; retain all images in an API request if needed.
- GET `/admin/inventory`; POST `/admin/inventory/{variant_id}/adjust` with signed integer `delta`, reason and low-stock threshold; cannot reduce physical units below reservations.
- GET `/admin/inventory/{variant_id}/movements` (paginated history).
- GET `/admin/orders`; POST `/admin/orders/{uuid}/status` with `processing`, `shipped`, `delivered` or `cancelled`; invalid transitions/unpaid fulfilment rejected.
- GET `/admin/customers`: paginated safe profile overview.

Admin product editor currently supports a primary image and basic variants; multi-image updates are supported by API, and advanced variant editing remains future UI work. Uploads are not accepted: only controlled local image paths are allowed, behind the image-path validation boundary. A reviewed external storage adapter is required before enabling uploaded assets.

## Payments and operations

POST `/payments/orders/{uuid}/initialize` and POST `/payments/webhook/{provider}` fail closed with 503 until a provider is approved/implemented. The provider Protocol defines initialization, server verification, authenticated webhook parsing, refunds and reconciliation. Internal event processing enforces order/payment locks, amount/currency verification, provider-event uniqueness, duplicate/stale handling, transactional stock consumption and late-payment reconciliation. No public endpoint accepts raw “paid” status. Timestamp replay-window checks precede configured webhook verification; provider-specific signature formats must be reviewed before activation.

GET `/health` is liveness; GET `/ready` performs a real database connectivity query. GET `/api/v1/environment` returns nonsecret mode/isolated-test guard status, used by browser tests to reject unsafe test environments. Reservation expiration is an explicit operational command; a supervised schedule is required for unattended release.
