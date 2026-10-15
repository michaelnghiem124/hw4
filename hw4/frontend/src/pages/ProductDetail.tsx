import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { API_BASE, fetchProduct, type ProductDetail as ProductDetailData } from '../lib/api';

export default function ProductDetail() {
  const { productId } = useParams<{ productId: string }>();
  const [product, setProduct] = useState<ProductDetailData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!productId) return;
    setProduct(null);
    setError(null);
    fetchProduct(productId)
      .then(setProduct)
      .catch((err) => setError(err.message));
  }, [productId]);

  if (error) {
    return (
      <section className="page-section container">
        <div className="section-head">
          <h1>Product not found</h1>
          <p>{error}</p>
        </div>
        <p className="result-count">
          <Link to="/products" className="link-rule">
            Back to all products
          </Link>
        </p>
      </section>
    );
  }

  if (!product) {
    return (
      <section className="page-section container">
        <p className="result-count">Loading product…</p>
      </section>
    );
  }

  const soldOut = product.sizes.filter((s) => s.quantity === 0).length;

  return (
    <section className="page-section container">
      <Link to="/products" className="back-link">
        ← All products
      </Link>
      <div className="product-detail">
        <div className="product-detail-media">
          <img src={`${API_BASE}${product.image_url}`} alt={product.name} />
        </div>
        <div className="product-detail-info">
          <span className="badge">{product.garment_type}</span>
          <h1>{product.name}</h1>
          <span className="product-detail-price">${product.price.toFixed(2)}</span>
          <p>{product.description}</p>

          <div className="spec-block">
            <span className="spec-label">Colors</span>
            <div className="swatch-row">
              {product.colors.map((color) => (
                <span className="swatch" key={color}>
                  {color}
                </span>
              ))}
            </div>
          </div>

          <div className="spec-block">
            <span className="spec-label">Sizes &amp; Stock</span>
            <div className="size-grid">
              {product.sizes.map((s) => (
                <span
                  key={s.size}
                  className={`size-pill ${s.quantity > 0 ? 'in-stock' : 'out-of-stock'}`}
                  title={s.quantity > 0 ? `${s.quantity} in stock` : 'Out of stock'}
                >
                  {s.size}
                </span>
              ))}
            </div>
            <p className="size-note">
              {soldOut === 0
                ? 'Every size is in stock right now.'
                : `${soldOut} ${soldOut === 1 ? 'size is' : 'sizes are'} sold out — struck through above.`}{' '}
              Ask Handsome Dan in the chat for exact counts.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
