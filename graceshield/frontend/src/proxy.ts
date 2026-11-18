import { NextResponse, type NextRequest } from 'next/server';
const routes = new Set([
  '/',
  '/shop',
  '/categories',
  '/cart',
  '/checkout',
  '/login',
  '/register',
  '/account',
  '/account/orders',
  '/about',
  '/contact',
  '/faq',
  '/delivery',
  '/returns',
  '/privacy',
  '/terms',
  '/forgot-password',
  '/verify-email',
  '/reset-password',
  '/admin',
  '/admin/products',
  '/admin/categories',
  '/admin/inventory',
  '/admin/orders',
  '/admin/customers',
]);
function missing(request: NextRequest) {
  return NextResponse.rewrite(new URL('/_not-found', request.url), {
    status: 404,
    headers: { 'X-Robots-Tag': 'noindex' },
  });
}
export async function proxy(request: NextRequest) {
  const path = request.nextUrl.pathname.replace(/\/$/, '') || '/';
  if (path === '/_not-found' || routes.has(path)) return NextResponse.next();
  const match = /^\/(products|categories)\/([a-z0-9]+(?:-[a-z0-9]+)*)$/.exec(path);
  if (!match) return missing(request);
  // Resolve missing resources before streaming can commit a 200 response.
  try {
    const origin = process.env.API_INTERNAL_URL ?? 'http://127.0.0.1:8000';
    const response = await fetch(`${origin}/api/v1/${match[1]}/${match[2]}`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(8000),
    });
    if (response.status === 404) return missing(request);
  } catch {
    /* The page renders the explicit unavailable-service state. */
  }
  return NextResponse.next();
}
export const config = { matcher: ['/((?!api/|_next/|images/|icon.svg|robots.txt|sitemap.xml).*)'] };
