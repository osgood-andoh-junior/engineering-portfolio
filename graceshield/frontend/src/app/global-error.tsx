'use client';
export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body>
        <main style={{ fontFamily: 'sans-serif', padding: '4rem', color: '#0B3B75' }}>
          <h1>GraceShield is temporarily unavailable.</h1>
          <p>Please try loading the page again.</p>
          <button onClick={reset}>Try again</button>
        </main>
      </body>
    </html>
  );
}
