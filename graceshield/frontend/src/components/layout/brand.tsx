import Link from 'next/link';
export function Brand() {
  return (
    <Link href="/" className="brand" aria-label="GraceShield home">
      <svg width="39" height="44" viewBox="0 0 44 50" fill="none" aria-hidden="true">
        <path
          d="M22 3 40 9v17c0 10-10 17-18 21C14 43 4 36 4 26V9L22 3Z"
          stroke="currentColor"
          strokeWidth="2.5"
        />
        <path
          d="M11 16c5-2 8-1 11 2 3-3 6-4 11-2v16c-5-2-8-1-11 2-3-3-6-4-11-2V16Zm11 2v16"
          stroke="currentColor"
          strokeWidth="2"
        />
      </svg>
      <span>
        GraceShield<small>FOR EVERY BRIGHTER CHAPTER</small>
      </span>
    </Link>
  );
}
