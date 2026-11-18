import { z } from 'zod';
export const checkoutSchema = z.object({
  firstName: z.string().trim().min(2, 'Enter your first name.').max(80),
  lastName: z.string().trim().min(2, 'Enter your last name.').max(80),
  email: z.email('Enter a valid email address.').max(254),
  phone: z
    .string()
    .trim()
    .regex(/^(?:\+233|0)[235]\d{8}$/, 'Enter a Ghana phone number, e.g. 0241234567.'),
  address: z.string().trim().min(5, 'Enter a delivery address.').max(200),
  region: z.string().refine((value) => regions.includes(value), 'Choose a region.'),
  city: z.string().trim().min(2, 'Enter a city or town.').max(100),
});
export type CheckoutDraft = z.infer<typeof checkoutSchema>;
export const regions = [
  'Ahafo',
  'Ashanti',
  'Bono',
  'Bono East',
  'Central',
  'Eastern',
  'Greater Accra',
  'North East',
  'Northern',
  'Oti',
  'Savannah',
  'Upper East',
  'Upper West',
  'Volta',
  'Western',
  'Western North',
];
