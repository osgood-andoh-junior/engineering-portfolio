import { it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TokenForm } from './token-form';
import { installApiFixture } from '../../../tests/helpers/api-fixtures';
it('reads one-time tokens from a fragment and removes them from browser history before submission', async () => {
  const raw = 'one-time-test-token-for-verification-only';
  window.history.replaceState(null, '', `/verify-email#token=${raw}`);
  const transport = installApiFixture();
  render(<TokenForm mode="verify" />);
  await waitFor(() => expect(screen.getByRole('button', { name: 'Verify email' })).toBeEnabled());
  expect(window.location.hash).toBe('');
  await userEvent.setup().click(screen.getByRole('button', { name: 'Verify email' }));
  await waitFor(() =>
    expect(
      transport.mock.calls.some(
        ([path, options]) =>
          String(path) === '/api/v1/auth/verification/confirm' &&
          JSON.parse(String(options?.body)).token === raw,
      ),
    ).toBe(true),
  );
  expect(transport.mock.calls.every(([path]) => !String(path).includes(raw))).toBe(true);
});
