import type { Metadata } from 'next';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/plus-jakarta-sans/500.css';
import '@fontsource/plus-jakarta-sans/600.css';
import '@fontsource/plus-jakarta-sans/700.css';
import './globals.css';
import { CartProvider } from '@/features/cart/cart-provider';
import { Header } from '@/components/layout/header';
import { Footer } from '@/components/layout/footer';
import { listCategories } from '@/features/catalogue/repository';
import { siteOrigin } from '@/lib/config';
export const metadata: Metadata = {
  metadataBase: siteOrigin,
  title: { default: 'GraceShield — For every brighter chapter', template: '%s | GraceShield' },
  description:
    'Explore the GraceShield frontend preview: books, stationery, learning and everyday essentials for Ghana. Demonstration inventory only.',
  robots: { index: false, follow: false },
  openGraph: {
    title: 'GraceShield — For every brighter chapter',
    description: 'A demonstration storefront for thoughtful learning and everyday essentials.',
    type: 'website',
    locale: 'en_GH',
  },
};
export const dynamic = 'force-dynamic';
export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const result = await listCategories();
  return (
    <html lang="en-GH">
      <body>
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        <CartProvider>
          <Header categories={result.ok ? result.data : []} />
          <main id="main">{children}</main>
          <Footer />
        </CartProvider>
      </body>
    </html>
  );
}
