"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api, clearTokens, getToken } from "./api";
import type { MeOut } from "./types";

interface AuthCtx {
  me: MeOut | null;
  loading: boolean;
  can: (perm: string) => boolean;
  refresh: () => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx>({
  me: null,
  loading: true,
  can: () => false,
  refresh: async () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<MeOut | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  async function load() {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    try {
      setMe(await api.get<MeOut>("/me"));
    } catch {
      clearTokens();
      setMe(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function can(perm: string): boolean {
    if (!me) return false;
    if (me.permissions.includes("*") || me.permissions.includes(perm)) return true;
    const mod = perm.split(".")[0];
    return me.permissions.includes(`${mod}.*`);
  }

  function logout() {
    clearTokens();
    setMe(null);
    router.push("/login");
  }

  return (
    <Ctx.Provider value={{ me, loading, can, refresh: load, logout }}>{children}</Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);
