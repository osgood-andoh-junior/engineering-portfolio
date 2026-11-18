import { it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProductCard } from './product-card';
import { CartProvider } from '@/features/cart/cart-provider';
import { installApiFixture, testProduct } from '../../../tests/helpers/api-fixtures';
it('links to product details, labels sample content and adds to cart', async () => {
  const user = userEvent.setup();
  installApiFixture();
  render(
    <CartProvider>
      <ProductCard product={testProduct} />
    </CartProvider>,
  );
  expect(screen.getByRole('heading', { name: testProduct.name })).toBeInTheDocument();
  expect(screen.getByText('SAMPLE')).toBeInTheDocument();
  const button = screen.getByRole('button', { name: `Add ${testProduct.name} to bag` });
  await waitFor(() => expect(button).toBeEnabled());
  await user.click(button);
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('updated'));
});
