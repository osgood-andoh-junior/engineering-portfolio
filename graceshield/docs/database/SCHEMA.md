# PostgreSQL schema and migration design

Initial revision: `backend/alembic/versions/0001_initial.py`, a frozen explicit PostgreSQL DDL snapshot generated offline from reviewed model declarations. It has **not** been applied to a cloud database in this task. Future changes require new Alembic revisions; do not rerun the initial snapshot generator to rewrite history. Operational migrations use the direct provider URL and reject production until separately approved.

| Area      | Tables and key relationships                                                                                                                                                             |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Identity  | `users` (unique normalized email), `roles`, `user_roles` (composite PK), `customer_profiles` (unique user), `addresses` (owner FK)                                                       |
| Security  | `sessions` (unique hashed opaque token, owner/expiry), `account_tokens` (hashed single-use token/purpose/expiry), `rate_limits` (hashed bucket key/count/expiry)                         |
| Catalogue | `categories` (unique slug, optional parent), `products` (category FK, unique slug, publication status), `product_variants` (unique SKU), `product_images` (controlled path/alt/position) |
| Stock     | `inventory` (variant PK/FK, quantity/reserved/threshold), `inventory_movements` (variant/actor/deltas/reason/time)                                                                       |
| Shopping  | `carts` (unique owner or guest session), `cart_items` (unique cart/variant, quantity 1–20)                                                                                               |
| Orders    | `orders` (owner/reference/idempotency/request fingerprint/customer snapshot/expiry/totals/status), `order_items` (variant/name/SKU/unit-price/quantity snapshots)                        |
| Payments  | `payments` (order/provider/reference/amount/status), `payment_events` (unique provider/event ID), `shipments` (unique order/status/tracking)                                             |
| Audit     | `audit_logs` (actor/action/resource/details/time)                                                                                                                                        |

22 tables. UUID identifiers are generated server-side. Timestamps are timezone-aware UTC. Monetary values are integer pesewas; currency is GHS. Check constraints enforce nonnegative prices, bounded cart quantities, stock `0 <= reserved <= quantity`, valid publication/order statuses and consistent order totals. FKs, unique constraints and indexes protect identity/lookup/order ownership and expiry queries.

Order-line snapshot fields have no mutation API and are treated as immutable after preparation. Backend transactions own totals and inventory; client prices/stock/roles/status are ignored or rejected. User/cart locks serialize concurrent mutation and idempotency checks, sorted product/stock locks prevent overselling, and advisory locks serialize expiration batches, hierarchy changes and admin bootstrap. PostgreSQL concurrency tests are prepared but require the guarded cloud test database before these guarantees can be claimed as empirically verified.

Production hardening must review indexes using real query plans/data volume, retention/deletion requirements for personal snapshots/security rows, outbox guarantees for email/events, audit-log access controls and backup/restore behavior. A full schema reset is not a normal development operation.
