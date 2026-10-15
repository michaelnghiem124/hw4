export const API_BASE = 'http://localhost:8000';

export interface ProductSummary {
  product_id: string;
  name: string;
  garment_type: string;
  description: string;
  colors: string[];
  price: number;
  image_url: string;
}

export interface ProductSize {
  size: string;
  quantity: number;
}

export interface ProductDetail extends ProductSummary {
  search_tags: string[];
  sizes: ProductSize[];
}

export interface Segment {
  id: string;
  label: string;
  blurb: string;
}

/** Audience curation lives in the API, next to the catalogue — see GET /api/segments. */
export async function fetchSegments(): Promise<Segment[]> {
  const res = await fetch(`${API_BASE}/api/segments`);
  if (!res.ok) throw new Error(`Failed to load segments (${res.status})`);
  return res.json();
}

export async function fetchProducts(
  options: { segment?: string | null; limit?: number } = {},
): Promise<ProductSummary[]> {
  const params = new URLSearchParams();
  if (options.segment) params.set('segment', options.segment);
  if (options.limit) params.set('limit', String(options.limit));
  const query = params.toString();
  const res = await fetch(`${API_BASE}/api/products${query ? `?${query}` : ''}`);
  if (!res.ok) throw new Error(`Failed to load products (${res.status})`);
  return res.json();
}

export async function fetchProduct(productId: string): Promise<ProductDetail> {
  const res = await fetch(`${API_BASE}/api/products/${productId}`);
  if (!res.ok) throw new Error(`Failed to load product (${res.status})`);
  return res.json();
}

export interface User {
  id: number;
  first_name: string;
  last_name: string;
  name: string;
  email: string;
  /** Signed by the server at sign-in. The only thing that proves who is chatting. */
  token: string;
}

/** Bearer header for the chat endpoints, which refuse to infer identity any other way. */
function authHeaders(token: string | null): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface SignupInput {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  confirm_password: string;
}

export interface LoginInput {
  email: string;
  password: string;
}

async function parseErrorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return body.detail ?? `Request failed (${res.status})`;
  } catch {
    return `Request failed (${res.status})`;
  }
}

export async function signup(input: SignupInput): Promise<User> {
  const res = await fetch(`${API_BASE}/api/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(await parseErrorMessage(res));
  return res.json();
}

export async function login(input: LoginInput): Promise<User> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(await parseErrorMessage(res));
  return res.json();
}

export interface ChatTurn {
  role: 'user' | 'assistant';
  content: string;
}

/** A product card the agent surfaced; every field is re-read from the DB by the API. */
export interface ChatProductCard {
  product_id: string;
  name: string;
  garment_type: string;
  description: string;
  price: number;
  image_url: string;
  in_stock: boolean;
}

export interface ChatResponse {
  reply: string;
  products: ChatProductCard[];
}

/** What the shopper has open when they send a message. */
export interface PageContext {
  path: string;
  product_id: string | null;
}

export interface StoredChatTurn extends ChatTurn {
  products: ChatProductCard[];
}

/**
 * Send one turn. `token` is null for guests, who get a normal guest session.
 *
 * No user id is sent: the server derives identity from the token alone, so
 * there is nothing here a client could change to become someone else.
 */
export async function sendChatMessage(
  message: string,
  history: ChatTurn[],
  token: string | null,
  pageContext: PageContext,
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
    body: JSON.stringify({ message, history, page_context: pageContext }),
  });
  if (!res.ok) throw new Error(await parseErrorMessage(res));
  return res.json();
}

/** The caller's own saved conversation, identified by their token. Guests have none. */
export async function fetchChatHistory(token: string): Promise<StoredChatTurn[]> {
  const res = await fetch(`${API_BASE}/api/chat/history`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(await parseErrorMessage(res));
  const body = await res.json();
  return body.messages;
}
