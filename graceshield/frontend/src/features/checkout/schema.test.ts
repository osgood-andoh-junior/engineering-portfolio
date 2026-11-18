import { it, expect } from 'vitest';
import { checkoutSchema } from './schema';
const draft = {
  firstName: 'Ama',
  lastName: 'Mensah',
  email: 'ama@example.test',
  phone: '0241234567',
  address: 'Sample address 12',
  region: 'Greater Accra',
  city: 'Accra',
};
it('validates local sample details including Ghana phone formats', () => {
  expect(checkoutSchema.safeParse(draft).success).toBe(true);
  expect(checkoutSchema.safeParse({ ...draft, phone: '+233241234567' }).success).toBe(true);
});
it('rejects missing details, invalid email and phone', () => {
  expect(
    checkoutSchema.safeParse({ ...draft, email: 'bad', phone: '123', firstName: '', region: '' })
      .success,
  ).toBe(false);
});
