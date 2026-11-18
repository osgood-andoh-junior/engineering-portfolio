import { it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CartProvider, useCart } from './cart-provider';
import { installApiFixture, productId, variantId } from '../../../tests/helpers/api-fixtures';
function Harness() {
  const cart = useCart();
  return (
    <>
      <span data-testid="count">{cart.count}</span>
      <span data-testid="subtotal">{cart.subtotal}</span>
      <button disabled={!cart.ready || cart.busy} onClick={() => cart.add(productId, 2, variantId)}>
        Add notebook
      </button>
      <button onClick={() => cart.remove(variantId)}>Remove notebook</button>
      <p role="alert">{cart.error}</p>
    </>
  );
}
it('restores backend cart, adds with CSRF, removes and announces', async () => {
  const transport = installApiFixture();
  const user = userEvent.setup();
  render(
    <CartProvider>
      <Harness />
    </CartProvider>,
  );
  await waitFor(() => expect(screen.getByText('Add notebook')).toBeEnabled());
  await user.click(screen.getByText('Add notebook'));
  await waitFor(() => expect(screen.getByTestId('count')).toHaveTextContent('2'));
  expect(screen.getByTestId('subtotal')).toHaveTextContent('9000');
  expect(screen.getByRole('status')).toHaveTextContent('updated');
  expect(
    transport.mock.calls.some(
      ([path, options]) => String(path).endsWith('/cart/items') && options?.method === 'POST',
    ),
  ).toBe(true);
  expect(localStorage.length).toBe(0);
  await user.click(screen.getByText('Remove notebook'));
  await waitFor(() => expect(screen.getByTestId('count')).toHaveTextContent('0'));
});
it('restores authoritative quantities rather than trusting old local storage', async () => {
  installApiFixture(3);
  localStorage.setItem('graceshield.cart.v1', 'oops');
  render(
    <CartProvider>
      <Harness />
    </CartProvider>,
  );
  await waitFor(() => expect(screen.getByTestId('count')).toHaveTextContent('3'));
  expect(screen.getByTestId('subtotal')).toHaveTextContent('13500');
});
