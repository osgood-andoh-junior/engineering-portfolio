import type { Money } from '@/features/catalogue/types';
export function formatMoney(money: Money | number): string {
  const minor = typeof money === 'number' ? money : money.amount;
  return new Intl.NumberFormat('en-GH', {
    style: 'currency',
    currency: 'GHS',
    currencyDisplay: 'code',
  }).format(minor / 100);
}
