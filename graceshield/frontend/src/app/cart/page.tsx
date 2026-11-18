import { CartView } from '@/features/cart/cart-view';
import { canonical } from '@/lib/metadata';
export const metadata = { title: 'Your shopping bag', alternates: canonical('/cart') };
export default function CartPage() {
  return (
    <div className="wrap page-space">
      <div className="page-heading">
        <p className="eyebrow">YOUR EVERYDAY FINDS</p>
        <h1>Your bag.</h1>
        <p>
          A few good things for your next chapter. Seeded demonstration items are marked SAMPLE.
        </p>
      </div>
      <CartView />
    </div>
  );
}
