import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  API_BASE,
  fetchProducts,
  fetchSegments,
  type ProductSummary,
  type Segment,
} from '../lib/api';

export default function Products() {
  const [searchParams, setSearchParams] = useSearchParams();
  const segment = searchParams.get('segment');
  const [products, setProducts] = useState<ProductSummary[] | null>(null);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSegments()
      .then(setSegments)
      .catch(() => {
        /* the filter bar is optional; the catalogue still renders */
      });
  }, []);

  useEffect(() => {
    setProducts(null);
    setError(null);
    fetchProducts({ segment })
      .then(setProducts)
      .catch((err) => setError(err.message));
  }, [segment]);

  const active = segments.find((s) => s.id === segment);

  function selectSegment(id: string | null) {
    setSearchParams(id ? { segment: id } : {});
  }

  return (
    <section className="page-section container">
      <div className="section-head">
        <div className="rule">
          <span />
        </div>
        <span className="eyebrow eyebrow-dark">The Collection</span>
        <h1>{active ? `For ${active.label}` : 'Everything We Make'}</h1>
        <p>
          {active
            ? active.blurb
            : 'The full Campus Customs catalogue — click any item for sizes and live stock.'}
        </p>
      </div>

      <div className="segment-bar">
        <button
          type="button"
          className={`segment-chip ${segment ? '' : 'is-active'}`}
          onClick={() => selectSegment(null)}
        >
          Everything
        </button>
        {segments.map((s) => (
          <button
            type="button"
            key={s.id}
            className={`segment-chip ${segment === s.id ? 'is-active' : ''}`}
            onClick={() => selectSegment(s.id)}
          >
            {s.label}
          </button>
        ))}
      </div>

      {error && <p className="result-count">Couldn't load products: {error}</p>}
      {!error && !products && <p className="result-count">Loading products…</p>}
      {products && (
        <p className="result-count">
          {products.length} {products.length === 1 ? 'item' : 'items'}
        </p>
      )}

      {products && (
        <div className="card-grid">
          {products.map((p) => (
            <Link to={`/products/${p.product_id}`} className="card" key={p.product_id}>
              <div className="card-media">
                <img
                  src={`${API_BASE}${p.image_url}`}
                  alt={p.name}
                  className="card-image"
                  loading="lazy"
                />
              </div>
              <div className="card-body">
                <span className="badge">{p.garment_type}</span>
                <h3>{p.name}</h3>
                <p className="card-description">{p.description.slice(0, 90)}…</p>
                <span className="card-price">${p.price.toFixed(2)}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
