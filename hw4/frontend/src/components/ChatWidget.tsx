import { useEffect, useState, type FormEvent } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  API_BASE,
  fetchChatHistory,
  sendChatMessage,
  type ChatProductCard,
  type ChatTurn,
  type PageContext,
} from '../lib/api';
import { useAuth } from '../lib/auth';
import { BulldogPhoto } from './Heraldry';

interface DisplayMessage extends ChatTurn {
  products?: ChatProductCard[];
}

const GREETING: DisplayMessage = {
  role: 'assistant',
  content:
    "Woof! I'm Handsome Dan, Yale's bulldog and your Campus Customs shopping buddy. Ask me " +
    'about products, sizes, or stock — I sniff out a good sweatshirt fast.',
};

function CloseMark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor">
      <path d="M5 5l14 14M19 5L5 19" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

/** Turn the current route into the context the agent needs to resolve "this". */
function readPageContext(pathname: string): PageContext {
  const match = pathname.match(/^\/products\/(.+)$/);
  return { path: pathname, product_id: match ? match[1] : null };
}

export default function ChatWidget() {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<DisplayMessage[]>([GREETING]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Signed-in shoppers pick up where they left off; guests always start fresh.
  useEffect(() => {
    if (!user) {
      setMessages([GREETING]);
      return;
    }
    let active = true;
    fetchChatHistory(user.token)
      .then((stored) => {
        if (!active) return;
        setMessages(stored.length ? [GREETING, ...stored] : [GREETING]);
      })
      .catch(() => {
        /* a failed replay shouldn't block a new conversation */
      });
    return () => {
      active = false;
    };
  }, [user]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || sending) return;

    const history: ChatTurn[] = messages.map(({ role, content }) => ({ role, content }));
    setMessages((prev) => [...prev, { role: 'user', content: trimmed }]);
    setInput('');
    setError(null);
    setSending(true);
    try {
      const res = await sendChatMessage(
        trimmed,
        history,
        user?.token ?? null,
        readPageContext(pathname),
      );
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.reply, products: res.products },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <button
        className="chat-toggle"
        onClick={() => setOpen((o) => !o)}
        aria-label="Toggle chat with Handsome Dan, the shopping assistant"
      >
        {open ? <CloseMark /> : <BulldogPhoto crop />}
      </button>

      {open && (
        <div className="chat-panel">
          <div className="chat-panel-header">
            <span className="dan-avatar">
              <BulldogPhoto crop />
            </span>
            <span>
              Handsome Dan
              <span className="chat-panel-subtitle">
                Campus Customs shopping assistant
              </span>
            </span>
          </div>
          <div className="chat-panel-body">
            <div className="chat-messages">
              {messages.map((m, i) => (
                <div
                  key={i}
                  className={`chat-message ${m.role === 'user' ? 'chat-message-user' : ''}`}
                >
                  {m.content}
                  {m.products && m.products.length > 0 && (
                    <div className="chat-product-cards">
                      {m.products.map((p) => (
                        <Link
                          key={p.product_id}
                          to={`/products/${p.product_id}`}
                          className="chat-product-card"
                        >
                          <img src={`${API_BASE}${p.image_url}`} alt={p.name} loading="lazy" />
                          <div className="chat-product-card-body">
                            <span className="chat-product-card-name">{p.name}</span>
                            <span className="chat-product-card-price">${p.price.toFixed(2)}</span>
                            <span className="chat-product-card-desc">{p.description}</span>
                            {!p.in_stock && (
                              <span className="chat-product-card-oos">Out of stock</span>
                            )}
                          </div>
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {sending && (
                <div className="chat-message chat-message-pending">Sniffing around…</div>
              )}
            </div>
          </div>
          <div className="chat-panel-footer">
            <p className="chat-session-note">
              {user ? (
                <>Signed in as {user.name} — this chat is saved to your account.</>
              ) : (
                <>
                  Chatting as a guest. <Link to="/login">Log in</Link> to save your chat.
                </>
              )}
            </p>
            {error && <p className="form-error">{error}</p>}
            <form className="chat-input-row" onSubmit={handleSubmit}>
              <input
                type="text"
                placeholder="Ask Handsome Dan about a product…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={sending}
              />
              <button type="submit" className="btn btn-primary" disabled={sending || !input.trim()}>
                Send
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
