import { Link } from 'react-router-dom';
import { CrestMark } from './Heraldry';

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="container">
        <div className="site-footer-inner">
          <div>
            <div className="site-footer-brand">
              <CrestMark />
              <span>Campus Customs</span>
            </div>
            <p className="site-footer-motto">New Haven · Worn Well</p>
          </div>
          <nav className="site-footer-links" aria-label="Footer">
            <Link to="/products">Shop All</Link>
            <Link to="/products?segment=students">Students</Link>
            <Link to="/products?segment=alumni">Alumni</Link>
            <Link to="/products?segment=family">Family</Link>
            <Link to="/about">Our Story</Link>
          </nav>
        </div>
        <p className="site-footer-legal">
          A student project for MGT 409. Not affiliated with or endorsed by Yale
          University.
        </p>
      </div>
    </footer>
  );
}
