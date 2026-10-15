import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  API_BASE,
  fetchProducts,
  fetchSegments,
  type ProductSummary,
  type Segment,
} from '../lib/api';
import { BulldogPhoto, CrestMark } from '../components/Heraldry';
import { HeroWall, Marquee, Reveal } from '../components/Motion';

interface SegmentCard extends Segment {
  cover: ProductSummary | null;
}

export default function Home() {
  const [featured, setFeatured] = useState<ProductSummary[]>([]);
  const [gallery, setGallery] = useState<ProductSummary[]>([]);
  const [segments, setSegments] = useState<SegmentCard[]>([]);

  // Every image on this page — the hero wall, the scrolling band, the segment
  // covers, the featured strip — is a real catalogue row. Nothing here is
  // decorative stock art, so the storefront can never show a garment or a
  // price the shop doesn't actually have.
  useEffect(() => {
    let active = true;

    fetchProducts({ limit: 4 })
      .then((products) => active && setFeatured(products))
      .catch(() => {});

    fetchProducts({ limit: 24 })
      .then((products) => active && setGallery(products))
      .catch(() => {});

    fetchSegments()
      .then(async (list) => {
        const withCovers = await Promise.all(
          list.map(async (segment) => {
            try {
              const [cover] = await fetchProducts({ segment: segment.id, limit: 1 });
              return { ...segment, cover: cover ?? null };
            } catch {
              return { ...segment, cover: null };
            }
          }),
        );
        if (active) setSegments(withCovers);
      })
      .catch(() => {});

    return () => {
      active = false;
    };
  }, []);

  return (
    <>
      {/* ---------------------------------------------------------- Hero -- */}
      <section className="hero-cinematic">
        <HeroWall products={gallery} />
        <div className="hero-veil" />
        <div className="container hero-inner">
          <CrestMark className="hero-crest" />
          <span className="eyebrow">New Haven, Connecticut</span>
          <h1>Ivy Heritage, Worn Well.</h1>
          <p className="hero-lede">
            Crewnecks for the walk down Elm Street, quarter-zips for reunion weekend,
            and a bulldog on the chest for everyone cheering in the stands. One
            hundred and two ways to wear the blue.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="btn btn-primary">
              Shop the Collection
            </Link>
            <Link to="/about" className="btn btn-outline">
              Our Story
            </Link>
          </div>
          <div className="pill-row">
            {segments.map((segment) => (
              <Link
                key={segment.id}
                to={`/products?segment=${segment.id}`}
                className="pill"
              >
                {segment.label}
              </Link>
            ))}
          </div>
          <p className="pill-row-hint">Shop a collection picked for you</p>
        </div>
        <div className="hero-scroll-cue" aria-hidden="true">
          Scroll
        </div>
      </section>

      {/* ------------------------------------------------ Panoramic band -- */}
      <section className="marquee-band">
        <p className="marquee-caption">Straight from the stockroom</p>
        <Marquee products={gallery} />
      </section>

      {/* ------------------------------------------------ Segment cards --- */}
      <section className="page-section band-paper">
        <div className="container">
          <Reveal>
            <div className="section-head">
              <div className="rule">
                <span />
              </div>
              <span className="eyebrow eyebrow-dark">Shop by Bulldog</span>
              <h2>Three Collections, One Campus</h2>
              <p>
                Students, alumni, and the family in the stands want genuinely
                different things. Start where you belong.
              </p>
            </div>
          </Reveal>
          <div className="segment-grid">
            {segments.map((segment, index) => (
              <Reveal key={segment.id} delay={index * 120}>
                <Link to={`/products?segment=${segment.id}`} className="segment-card">
                  {segment.cover && (
                    <img
                      src={`${API_BASE}${segment.cover.image_url}`}
                      alt=""
                      loading="lazy"
                    />
                  )}
                  <div className="segment-card-body">
                    <h3>{segment.label}</h3>
                    <p>{segment.blurb}</p>
                    <span className="segment-card-cta">Shop {segment.label}</span>
                  </div>
                </Link>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------------------------------------- Editorial band 1 -- */}
      <section className="page-section">
        <div className="container">
          <Reveal>
            <div className="editorial">
              <div className="editorial-media">
                {gallery[6] && (
                  <img
                    src={`${API_BASE}${gallery[6].image_url}`}
                    alt={gallery[6].name}
                    loading="lazy"
                  />
                )}
              </div>
              <div className="editorial-body">
                <span className="eyebrow eyebrow-dark">The House Style</span>
                <h2>Built for the long walk home.</h2>
                <p>
                  Heavyweight fleece, reverse-weave cotton, and shields that have
                  looked the same since your grandmother wore one. We stock the
                  pieces people actually keep — the hoodie that survives four New
                  Haven winters, not the one that survives one tailgate.
                </p>
                <div className="editorial-stats">
                  <div className="editorial-stat">
                    <strong>102</strong>
                    <span>Styles in stock</span>
                  </div>
                  <div className="editorial-stat">
                    <strong>XS–XXL</strong>
                    <span>Every size, every style</span>
                  </div>
                  <div className="editorial-stat">
                    <strong>1889</strong>
                    <span>Handsome Dan, since</span>
                  </div>
                </div>
                <Link to="/products" className="link-rule">
                  Browse all 102
                </Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ------------------------------------------------------ Featured -- */}
      <section className="page-section band-paper">
        <div className="container">
          <Reveal>
            <div className="section-head">
              <div className="rule">
                <span />
              </div>
              <span className="eyebrow eyebrow-dark">Featured This Week</span>
              <h2>On the Front Table</h2>
            </div>
          </Reveal>
          <div className="card-grid">
            {featured.map((item, index) => (
              <Reveal key={item.product_id} delay={index * 90}>
                <Link className="card" to={`/products/${item.product_id}`}>
                  <div className="card-media">
                    <img
                      className="card-image"
                      src={`${API_BASE}${item.image_url}`}
                      alt={item.name}
                      loading="lazy"
                    />
                  </div>
                  <div className="card-body">
                    <span className="badge">{item.garment_type}</span>
                    <h3>{item.name}</h3>
                    <span className="card-price">${item.price.toFixed(2)}</span>
                  </div>
                </Link>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ------------------------------------- Editorial band 2 — the dog -- */}
      <section className="page-section band-blue">
        <div className="container">
          <Reveal>
            <div className="editorial editorial-reverse">
              <div className="dan-panel">
                <BulldogPhoto />
              </div>
              <div className="editorial-body">
                <span className="eyebrow">Ask the Mascot</span>
                <h2>Handsome Dan is in the shop.</h2>
                <p>
                  Yale's bulldog has been on this campus since 1889, and he now works
                  the floor. Ask him what's in your size, what a Davenport crewneck
                  costs, or what to send your mother — he reads the stockroom live, so
                  he'll never promise you something that isn't on the shelf.
                </p>
                <p className="dan-prompt">
                  “Woof — XS, S and M are all in. XL is down to two, so move quickly.”
                </p>
              </div>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
