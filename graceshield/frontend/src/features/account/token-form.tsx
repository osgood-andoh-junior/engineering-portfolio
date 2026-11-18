'use client';
import { useState, useEffect } from 'react';
import { api, errorMessage, messageSchema } from '@/lib/api';
export function TokenForm({
  mode,
  token,
}: {
  mode: 'verify' | 'request-reset' | 'reset';
  token?: string;
}) {
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [activeToken, setActiveToken] = useState(token ?? '');
  useEffect(() => {
    const consumeToken = () => {
      const fromFragment = new URLSearchParams(window.location.hash.slice(1)).get('token');
      if (fromFragment) {
        queueMicrotask(() => setActiveToken(fromFragment));
        window.history.replaceState(null, '', window.location.pathname);
      }
    };
    consumeToken();
    window.addEventListener('hashchange', consumeToken);
    return () => window.removeEventListener('hashchange', consumeToken);
  }, []);
  return (
    <form
      className="content-card"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError('');
        const form = new FormData(e.currentTarget);
        const path =
          mode === 'verify'
            ? '/auth/verification/confirm'
            : mode === 'reset'
              ? '/auth/password/confirm'
              : '/auth/password/request';
        const body =
          mode === 'request-reset'
            ? { email: form.get('email') }
            : mode === 'reset'
              ? { token: activeToken, password: form.get('password') }
              : { token: activeToken };
        try {
          setMessage(
            (await api(path, messageSchema, { method: 'POST', body: JSON.stringify(body) }))
              .message,
          );
        } catch (e) {
          setError(errorMessage(e));
        } finally {
          setBusy(false);
        }
      }}
    >
      {mode === 'request-reset' && (
        <label className="form-field">
          Email address
          <input name="email" type="email" autoComplete="email" required />
        </label>
      )}
      {mode === 'reset' && (
        <label className="form-field">
          New password
          <input
            name="password"
            type="password"
            autoComplete="new-password"
            minLength={12}
            maxLength={128}
            required
          />
        </label>
      )}
      <button
        className="button primary"
        disabled={busy || (mode !== 'request-reset' && !activeToken)}
      >
        {busy
          ? 'Please wait…'
          : mode === 'verify'
            ? 'Verify email'
            : mode === 'reset'
              ? 'Reset password'
              : 'Request reset email'}
      </button>
      {message && <p role="status">{message}</p>}
      {error && (
        <p role="alert" className="field-error">
          {error}
        </p>
      )}
    </form>
  );
}
