# Architecture

> Historical frontend-only architecture. Current architecture is documented in `SYSTEM_OVERVIEW.md`.

Next.js App Router with React Server Components for read-oriented pages and minimal interactive client boundaries. Strict TypeScript, Tailwind v4 theme tokens plus semantic component CSS. Locally bundled Inter and Plus Jakarta Sans avoid runtime font dependencies. Radix Dialog owns focus trapping, escape and focus return in mobile navigation. Lucide supplies interface icons.

## Modules

- `src/data/mock`: deterministic sample categories/products, isolated from presentation.
- `features/catalogue`: typed product repository, pure query transformation and URL parsing; server-rendered catalogue composition.
- `features/products`: interactive gallery.
- `features/cart`: pure state reducer, schema-validated versioned persistence, narrow React context, product purchase/cart controls.
- `features/checkout`: validation schema and local form preview. No transport or order creation.
- `features/account`: disabled credential interface. No fake session.
- `components/layout` and `components/ui`: shared shell, category icons and product cards.
- `lib`: currency, validated environment configuration.

The mock repository is the service composition boundary. There are no fake API endpoints. It returns discriminated results and handles absent product slugs explicitly. UI consumes domain types; untrusted future responses must be schema-validated inside an API adapter, not asserted into types.

## Models and state

Product, ProductImage, Category, Money, InventoryAvailability, CartItem, Cart and CheckoutDraft are implemented. Product variants are not needed by the fixtures. Future customer profiles, addresses, variants, authoritative orders/order lines and payment states belong in the backend contract before adding frontend consumers. No invented backend entities are persisted.

Money is integer pesewas in GHS. Display converts to a formatted decimal only at the presentation edge. All quantities/prices/stock and subtotals are provisional. Cart storage contains only version, product IDs and integer quantities (1–20). Storage is restored after hydration; unknown/unavailable products are removed, duplicates merged, malformed data recovered. Unavailable browser storage degrades to in-memory shopping. Simultaneous tabs are last-writer-wins; no cross-device or cross-tab synchronization is promised.

## Rendering and caching

Home and product routes are suitable for static generation using deterministic fixtures. Catalogue query parameters render server-side; standard GET forms and links preserve refresh/back/forward behavior. No public customer response caching exists. Future inventory needs explicit TTLs/tags and invalidation on price/stock updates; real checkout always revalidates independently. Customer-specific routes must use private/no-store responses and server-side authentication/authorization.

## Design assumptions

No approved Figma or asset was available. Supplied palette and typography drive a restrained navy/ivory storefront. The shield-and-book mark and SVG product art are provisional, clearly documented for review. Actual photography, inventory and founder-approved content must replace samples before launch. SVG artwork is repository-native deterministic code, regenerated with `node scripts/generate-art.mjs`.
