import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import type { User } from './api';

const STORAGE_KEY = 'campus-customs-user';

interface AuthValue {
  user: User | null;
  signIn: (user: User) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthValue>({
  user: null,
  signIn: () => {},
  signOut: () => {},
});

function readStoredUser(): User | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const stored = JSON.parse(raw) as Partial<User>;
    // A session saved before chat required a signed token has no token, and a
    // tokenless user would look signed in while every chat call 401s. Treat it
    // as signed out and make them log in once.
    if (!stored?.token) return null;
    return stored as User;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(readStoredUser);

  useEffect(() => {
    if (user) localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    else localStorage.removeItem(STORAGE_KEY);
  }, [user]);

  return (
    <AuthContext.Provider
      value={{ user, signIn: setUser, signOut: () => setUser(null) }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
