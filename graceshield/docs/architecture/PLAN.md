# Implementation plan and inspection

Workspace inspected on 2026-10-15: empty; no Git repository, existing assets, Figma URL, or previous PRD. The attached master instructions are the sole available specification.

1. Foundation: strict Next.js App Router, TypeScript, Tailwind, local fonts, typed domain and isolated mock repository.
2. Storefront: responsive navy/ivory design, provisional shield/book mark, 11 exact categories, deterministic sample catalogue, URL search/filter/sort/pagination, product gallery.
3. Shopping: pure cart reducer, validated minimal persistence, accessible cart feedback, checkout validation with no order/payment submission.
4. Supporting pages: unavailable authentication interfaces, informational drafts, errors, metadata and indexing protections.
5. Quality: unit/component/integration tests, desktop/mobile Playwright, axe checks, CI, security and integration documentation.

## Assumptions and risks

- No approved logo or Figma is present. Use a provisional shield/book drawing and supplied color/type tokens; final design sign-off remains required.
- All inventory, availability and prices are demonstration fixtures, explicitly labeled; no reviews, discounts, sales claims, contact details or promises are fabricated.
- Policies are draft status pages requiring founder approval. No business rules are inferred.
- All cart information is local/provisional. Personal details stay in form memory. No credentials, messages, orders or payments are sent or saved.
- Backend services, auth, payment, shipping, notification and administration are outside this phase.
- No deployment, remote repository creation, or push is authorized.
