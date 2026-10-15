import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { API_BASE, fetchProducts, type ProductSummary } from '../lib/api';
import { BulldogPhoto, CrestMark } from '../components/Heraldry';
import { Reveal } from '../components/Motion';

export default function AboutUs() {
  const [gallery, setGallery] = useState<ProductSummary[]>([]);

  useEffect(() => {
    let active = true;
    fetchProducts({ limit: 12 })
      .then((products) => active && setGallery(products))
      .catch(() => {
        /* the page reads fine without the photography */
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <>
      <section className="page-section band-blue">
        <div className="container">
          <div className="section-head">
            <CrestMark className="hero-crest" />
            <span className="eyebrow">Est. New Haven</span>
            <h1>Yale Pride, Made Wearable.</h1>
            <p>
              For everyone who has ever called this campus home — and for everyone who
              drove up to visit.
            </p>
          </div>
        </div>
      </section>

      <section className="page-section">
        <div className="container">
          <Reveal>
            <div className="editorial">
              <div className="editorial-media">
                {gallery[2] && (
                  <img
                    src={`${API_BASE}${gallery[2].image_url}`}
                    alt={gallery[2].name}
                    loading="lazy"
                  />
                )}
              </div>
              <div className="editorial-body">
                <span className="eyebrow eyebrow-dark">Who We Serve</span>
                <h2>Three audiences, one wardrobe.</h2>
                <p>
                  A sophomore wants her residential college crewneck. A classmate from
                  '04 wants the shield he remembers. A grandmother in the stands wants
                  something that says exactly whose grandmother she is. We built the
                  shop around those three errands instead of one undifferentiated wall
                  of merchandise.
                </p>
                <div className="editorial-stats">
                  <div className="editorial-stat">
                    <strong>Students</strong>
                    <span>Residential colleges &amp; varsity</span>
                  </div>
                  <div className="editorial-stat">
                    <strong>Alumni</strong>
                    <span>Crests, grad schools, The Game</span>
                  </div>
                  <div className="editorial-stat">
                    <strong>Family</strong>
                    <span>Mom, Dad, and Handsome Dan</span>
                  </div>
                </div>
                <Link to="/products" className="link-rule">
                  Shop the collections
                </Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      <section className="page-section band-paper">
        <div className="container">
          <Reveal>
            <div className="editorial editorial-reverse">
              <div className="editorial-media">
                {gallery[7] && (
                  <img
                    src={`${API_BASE}${gallery[7].image_url}`}
                    alt={gallery[7].name}
                    loading="lazy"
                  />
                )}
              </div>
              <div className="editorial-body">
                <span className="eyebrow eyebrow-dark">Our Mission</span>
                <h2>Never promise what isn't on the shelf.</h2>
                <p>
                  Every price and every size you see here is read from the stockroom at
                  the moment the page loads — never estimated, never cached into a
                  marketing blurb. The same rule binds our chat assistant: he quotes
                  the database or he says he doesn't know.
                </p>
                <p>
                  It's an unglamorous promise, but it's the one that decides whether
                  you order from us twice.
                </p>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      <section className="page-section band-blue">
        <div className="container">
          <Reveal>
            <div className="editorial">
              <div className="dan-panel">
                <BulldogPhoto />
              </div>
              <div className="editorial-body">
                <span className="eyebrow">Our Floor Staff</span>
                <h2>Handsome Dan, Class of 1889.</h2>
                <p>
                  Yale's bulldog mascot is the oldest live mascot in American college
                  sport, and he keeps shop hours here. Ask him for a recommendation,
                  a size, or an honest opinion of Harvard.
                </p>
                <p className="dan-prompt">
                  “I've been patrolling this campus longer than most of the buildings.”
                </p>
              </div>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
