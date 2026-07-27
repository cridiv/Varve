import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export interface VarveUserIdentity {
  username: string;
  name: string;
  initials: string;
  role: string;
}

/**
 * Returns the current user identity from localStorage, or null if not authenticated.
 * On the server side (SSR), always returns null until the component mounts.
 *
 * @param redirectIfUnauthenticated - if true, redirects to /connect when no identity is found
 */
export function useAuth(redirectIfUnauthenticated = false): {
  user: VarveUserIdentity | null;
  isLoading: boolean;
} {
  const router = useRouter();
  const [user, setUser] = useState<VarveUserIdentity | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    try {
      const raw = localStorage.getItem("varve_user_identity");
      if (raw) {
        setUser(JSON.parse(raw) as VarveUserIdentity);
      } else if (redirectIfUnauthenticated) {
        router.replace("/connect");
      }
    } catch {
      if (redirectIfUnauthenticated) {
        router.replace("/connect");
      }
    } finally {
      setIsLoading(false);
    }
  }, [redirectIfUnauthenticated, router]);

  return { user, isLoading };
}
