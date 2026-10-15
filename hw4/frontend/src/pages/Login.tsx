import { useState, type FormEvent } from 'react';
import { login } from '../lib/api';
import { useAuth } from '../lib/auth';

export default function Login() {
  const { user, signIn, signOut } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      signIn(await login({ email, password }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setSubmitting(false);
    }
  }

  if (user) {
    return (
      <section className="page-section container">
        <div className="section-head">
          <div className="rule">
            <span />
          </div>
          <span className="eyebrow eyebrow-dark">Your Account</span>
          <h1>Welcome Back</h1>
          <p>
            You're logged in as {user.name}. Your chat with Handsome Dan is saved to
            your account, so it'll be waiting for you next time.
          </p>
          <button type="button" className="btn btn-ghost" onClick={signOut}>
            Log Out
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="page-section container">
      <div className="section-head">
        <div className="rule">
          <span />
        </div>
        <span className="eyebrow eyebrow-dark">Members</span>
        <h1>Welcome Back</h1>
        <p>Log in to pick up where you left off.</p>
      </div>

      <form className="form-card" onSubmit={handleSubmit}>
        <div className="form-field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            name="email"
            type="email"
            placeholder="you@yale.edu"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div className="form-field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        {error && <p className="form-error">{error}</p>}
        <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={submitting}>
          {submitting ? 'Logging in…' : 'Log In'}
        </button>
        <p className="form-footnote">
          New here? <a href="/create-account">Create an account</a>
        </p>
      </form>
    </section>
  );
}
