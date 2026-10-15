import { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { CrestMark } from './Heraldry';
import './NavBar.css';

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Shop' },
  { to: '/about', label: 'Our Story' },
];

const accountLinks = [
  { to: '/login', label: 'Login' },
  { to: '/create-account', label: 'Create Account' },
];

export default function NavBar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { pathname } = useLocation();

  // Over the home hero the masthead is transparent; everywhere else — and as
  // soon as the page moves — it goes solid so the links stay legible against
  // whatever is scrolling underneath.
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const transparent = pathname === '/' && !scrolled && !open;

  return (
    <header
      className={`site-header${scrolled ? ' is-scrolled' : ''}${
        transparent ? ' is-transparent' : ''
      }`}
    >
      <div className="header-rail">
        Complimentary shipping over $75 &nbsp;·&nbsp; Shipped from New Haven
      </div>
      <div className="navbar-inner">
        <NavLink to="/" className="navbar-brand" onClick={() => setOpen(false)}>
          <CrestMark />
          <span>
            <span className="navbar-wordmark">Campus Customs</span>
            <span className="navbar-tagline">Ivy Heritage</span>
          </span>
        </NavLink>

        <button
          type="button"
          className="navbar-toggle"
          aria-label="Toggle navigation menu"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          ☰
        </button>

        <ul className={`navbar-links${open ? ' open' : ''}`}>
          {links.map(({ to, label, end }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={end}
                className={({ isActive }) => (isActive ? 'active' : undefined)}
                onClick={() => setOpen(false)}
              >
                {label}
              </NavLink>
            </li>
          ))}
          {accountLinks.map(({ to, label }) => (
            <li key={to}>
              <NavLink
                to={to}
                className={({ isActive }) =>
                  isActive ? 'nav-account active' : 'nav-account'
                }
                onClick={() => setOpen(false)}
              >
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </div>
    </header>
  );
}
