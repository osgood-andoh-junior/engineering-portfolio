import { it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CartProvider } from '@/features/cart/cart-provider';
import { installApiFixture } from '../../../tests/helpers/api-fixtures';
import { CheckoutForm } from './checkout-form';
it('validates checkout fields before preparing an order and never enables live payments', async () => {
  const transport = installApiFixture(1);
  render(
    <CartProvider>
      <CheckoutForm />
    </CartProvider>,
  );
  await waitFor(() =>
    expect(
      screen.getByRole('button', { name: 'Prepare pending-payment order' }),
    ).toBeInTheDocument(),
  );
  await userEvent
    .setup()
    .click(screen.getByRole('button', { name: 'Prepare pending-payment order' }));
  expect(await screen.findByText('Enter your first name.')).toHaveAttribute('role', 'alert');
  expect(screen.getByRole('button', { name: 'Pay now — unavailable' })).toBeDisabled();
  expect(transport.mock.calls.some(([path]) => String(path).includes('/checkout/prepare'))).toBe(
    false,
  );
  expect(screen.getByLabelText('First name')).toHaveFocus();
});
