'use client';

import { useEffect, useRef, useState } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/store';
import { addEvent, setConnectionStatus } from '@/store/slices/relaySlice';
import { BuzzRelayClient } from '@/services/nostr-client';

export function useBuzzRelay(relayUrl: string, userSk: string | null) {
  const dispatch = useAppDispatch();
  const clientRef = useRef<BuzzRelayClient | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    if (!relayUrl) return;

    const client = new BuzzRelayClient(relayUrl);
    clientRef.current = client;

    if (userSk) {
      const skBytes = new Uint8Array(Buffer.from(userSk, 'hex'));
      client.setAuthKeys(skBytes);
      setIsAuthenticated(true);
    }

    dispatch(setConnectionStatus('connecting'));

    // Inscrição genérica para testar conexão e pegar eventos do sistema (Kind 1000, 30078, etc)
    // Em produção, isso virá de componentes específicos (ex: useChannel, useDM)
    const sub = client.subscribe(
      [{ kinds: [1, 1000], limit: 50 }],
      (event: any) => {
        dispatch(addEvent(event));
      },
      () => {
        dispatch(setConnectionStatus('connected')); // EOSE (End of Stored Events)
      }
    );

    return () => {
      sub.close();
      client.disconnect();
    };
  }, [relayUrl, userSk, dispatch]);

  const publishEvent = async (kind: number, content: string, tags: string[][] = []) => {
    if (!clientRef.current) return;
    return clientRef.current.publish({ kind, content, tags, created_at: Math.floor(Date.now() / 1000) });
  };

  return { publishEvent, isAuthenticated };
}
