import { AccountForm } from '@/features/account/account-form';
import { canonical } from '@/lib/metadata';
export const metadata = { title: 'Create an account preview', alternates: canonical('/register') };
export default function Register() {
  return (
    <div className="wrap auth-page">
      <AccountForm registration />
    </div>
  );
}
