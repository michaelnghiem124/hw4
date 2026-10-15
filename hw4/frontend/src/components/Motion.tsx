import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { API_BASE, type ProductSummary } from '../lib/api';

/**
 * Scroll-triggered fade-and-rise.
 *
 * The reference site (yaleclubnyc.org) uses video to make scrolling feel alive.
 * We can't ship video — product photography isn't committed to this repo — so
 * the liveliness comes from content arriving as you reach it. IntersectionObserver
 * rather than a scroll listener so it costs nothing on the main thread, and
 * `unobserve` on first hit so a band never re-animates on the way back up.
 */
export function Reveal({
  children,
  delay = 0,
  className = '',
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.unobserve(entry.target);
        }
      },
      { threshold: 0.12, rootMargin: '0px 0px -60px 0px' },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`reveal${visible ? ' is-visible' : ''}${className ? ` ${className}` : ''}`}
      style={delay ? { transitionDelay: `${delay}ms` } : undefined}
    >
      {children}
    </div>
  );
}

/**
 * The panoramic sweep: an endlessly scrolling band of real catalogue photography.
 *
 * The track is rendered twice and the keyframe translates it exactly -50%, so the
 * second copy lands where the first began and the loop is seamless. Hovering
 * pauses it, because a moving target you can't click is hostile in a store.
 */
export function Marquee({ products }: { products: ProductSummary[] }) {
  if (products.length === 0) return null;
  const track = [...products, ...products];

  return (
    <div className="marquee" aria-label="Browse the catalogue">
      <div className="marquee-track">
        {track.map((product, index) => (
          <Link
            key={`${product.product_id}-${index}`}
            to={`/products/${product.product_id}`}
            className="marquee-item"
            aria-hidden={index >= products.length}
            tabIndex={index >= products.length ? -1 : undefined}
          >
            <img
              src={`${API_BASE}${product.image_url}`}
              alt={index >= products.length ? '' : product.name}
              loading="lazy"
            />
          </Link>
        ))}
      </div>
    </div>
  );
}

/**
 * The hero backdrop: catalogue photos tiled into six columns and drifted slowly
 * with a Ken Burns scale, then flattened under a blue duotone veil so the whole
 * wall reads as one image rather than a contact sheet. This is the stand-in for
 * the club site's full-bleed video — same feeling of depth and movement, built
 * at runtime from data the repo is allowed to carry.
 */
export function HeroWall({ products }: { products: ProductSummary[] }) {
  if (products.length === 0) return null;

  const columns = 6;
  const perColumn = 3;
  const tiles = Array.from({ length: columns }, (_, col) =>
    Array.from(
      { length: perColumn },
      (_, row) => products[(col * perColumn + row) % products.length],
    ),
  );

  return (
    <div className="hero-wall" aria-hidden="true">
      {tiles.map((column, colIndex) => (
        <div className="hero-wall-col" key={colIndex}>
          {column.map((product, rowIndex) => (
            <img
              key={`${product.product_id}-${colIndex}-${rowIndex}`}
              src={`${API_BASE}${product.image_url}`}
              alt=""
              loading={colIndex < 3 ? 'eager' : 'lazy'}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
