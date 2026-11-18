'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import * as Dialog from '@radix-ui/react-dialog';
import { Search, ShoppingBag, UserRound, Menu, X, ArrowUpRight, ChevronDown } from 'lucide-react';
import { useState } from 'react';
import { useCart } from '@/features/cart/cart-provider';
import type { Category } from '@/features/catalogue/types';
import { Brand } from './brand';
export function Header({ categories }: { categories: Category[] }) {
  const { count } = useCart();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  return (
    <>
      <div className="demo-bar">
        A little preview of something good. <span>Local development · Live payments disabled</span>
        <Link href="/about">
          Meet GraceShield <ArrowUpRight size={12} />
        </Link>
      </div>
      <header className="site-header">
        <div className="header-main wrap">
          <Brand />
          <form action="/shop" className="header-search" role="search">
            <Search size={19} aria-hidden="true" />
            <input
              type="search"
              name="q"
              aria-label="Search products"
              placeholder="Find your next everyday essential…"
              maxLength={120}
            />
            <button aria-label="Submit product search">
              <ArrowUpRight size={19} />
            </button>
          </form>
          <div className="header-actions">
            <Link href="/account" className="account-link" aria-label="My account">
              <UserRound size={21} />
              <span>My account</span>
            </Link>
            <Link href="/cart" className="bag-link" aria-label={`Shopping bag, ${count} items`}>
              <ShoppingBag size={22} />
              <span className="bag-count">{count}</span>
            </Link>
            <Dialog.Root open={open} onOpenChange={setOpen}>
              <Dialog.Trigger className="icon-button mobile-menu" aria-label="Open navigation">
                <Menu />
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Overlay className="dialog-overlay" />
                <Dialog.Content className="mobile-panel">
                  <Dialog.Title>Explore GraceShield</Dialog.Title>
                  <Dialog.Description>
                    Shop by category or visit our information pages.
                  </Dialog.Description>
                  <Dialog.Close className="icon-button dialog-close" aria-label="Close navigation">
                    <X />
                  </Dialog.Close>
                  <nav aria-label="Mobile navigation">
                    {[
                      ['Home', '/'],
                      ['Shop all', '/shop'],
                      ['Categories', '/categories'],
                      ['About us', '/about'],
                      ['Contact', '/contact'],
                      ['My account', '/account'],
                      ...categories.map((c) => [c.name, `/categories/${c.slug}`]),
                    ].map(([label, href]) => (
                      <Link key={href} href={href} onClick={() => setOpen(false)}>
                        {label}
                        <ArrowUpRight size={15} />
                      </Link>
                    ))}
                  </nav>
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>
          </div>
        </div>
        <div className="nav-border">
          <nav className="wrap desktop-nav" aria-label="Main navigation">
            <Link href="/categories" className="browse-link">
              <Menu size={17} /> Browse categories <ChevronDown size={14} />
            </Link>
            <div className="nav-links">
              {[
                ['Home', '/'],
                ['Shop all', '/shop'],
                ['School essentials', '/categories/school-supplies'],
                ['Books & learning', '/categories/books-publications'],
                ['About us', '/about'],
              ].map(([label, href]) => (
                <Link key={href} href={href} aria-current={pathname === href ? 'page' : undefined}>
                  {label}
                </Link>
              ))}
            </div>
            <Link href="/contact" className="help-link">
              A question? Let’s help <ArrowUpRight size={14} />
            </Link>
          </nav>
        </div>
      </header>
    </>
  );
}
