import { CheckoutForm } from '@/features/checkout/checkout-form';
import { canonical } from '@/lib/metadata';
export const metadata = { title: 'Checkout preview', alternates: canonical('/checkout') };
export default function Checkout() {
  return (
    <div className="wrap page-space">
      <div className="page-heading">
        <p className="eyebrow">A LOOK AT WHAT’S NEXT</p>
        <h1>Prepare your order.</h1>
        <p>The backend validates prices, stock and delivery. Live payments remain disabled.</p>
      </div>
      <CheckoutForm />
    </div>
  );
}
