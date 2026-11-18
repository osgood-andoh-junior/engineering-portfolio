'use client';
import Image from 'next/image';
import { useState } from 'react';
import type { ProductImage } from '@/features/catalogue/types';
export function Gallery({ images }: { images: ProductImage[] }) {
  const [selected, setSelected] = useState(0);
  return (
    <div className="gallery">
      <div className="gallery-main">
        <span className="sample-tag">SAMPLE ILLUSTRATION</span>
        <Image
          src={images[selected].src}
          alt={images[selected].alt}
          width={600}
          height={520}
          priority
          style={{ transform: selected === 1 ? 'rotate(-8deg) scale(.9)' : undefined }}
        />
      </div>
      <div className="gallery-thumbs" aria-label="Product images">
        {images.map((img, i) => (
          <button
            key={i}
            aria-label={`View product image ${i + 1}`}
            aria-pressed={selected === i}
            onClick={() => setSelected(i)}
          >
            <Image
              src={img.src}
              alt=""
              width={72}
              height={65}
              style={{ transform: i === 1 ? 'rotate(-8deg)' : undefined }}
            />
          </button>
        ))}
      </div>
      <p className="muted small">Illustrative artwork. Actual product photography is pending.</p>
    </div>
  );
}
