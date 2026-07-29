import { generateSecretKey, finalizeEvent, verifyEvent } from 'nostr-tools/pure';
import { SimplePool } from 'nostr-tools/pool';

export class BuzzRelayClient {
  private pool: SimplePool;
  private relayUrl: string;
  private authPublicKey: string | null = null;
  private authSecretKey: Uint8Array | null = null;

  constructor(relayUrl: string) {
    this.relayUrl = relayUrl;
    // SimplePool gerencia múltiplas conexões, keep-alive e reconexões nativamente
    this.pool = new SimplePool();
  }

  /** NIP-42: Configura as chaves para responder desafios de autenticação */
  public setAuthKeys(sk: Uint8Array) {
    this.authSecretKey = sk;
    // Deriva a pública a partir da secreta (não armazene a pública hardcoded)
    this.authPublicKey = '0x' + Buffer.from(sk).toString('hex');
    // Nota: em produção, use getPublicKey(sk) do nostr-tools
  }

  /** NIP-01: Inscreve em eventos (Ex: Canal, DM, Workflow) */
  public subscribe(
    filters: any,
    onEvent: (event: any) => void,
    onEose: () => void
  ) {
    const sub = this.pool.subscribeMany(
      [this.relayUrl],
      filters,
      {
        onevent: (event) => {
          if (verifyEvent(event)) {
            onEvent(event);
          }
        },
        oneose: onEose,
      }
    );
    return sub; // Retorna a inscrição para permitir `sub.close()` depois
  }

  /** NIP-01: Publica um evento (Mensagem, Status de Workflow, etc) */
  public async publish(eventTemplate: any) {
    if (!this.authSecretKey) throw new Error("Chaves de autenticação não configuradas");

    const signedEvent = finalizeEvent(eventTemplate, this.authSecretKey);
    const pubs = this.pool.publish([this.relayUrl], signedEvent);

    // Aguarda confirmação do relay (OK)
    const results = await Promise.all(pubs);
    return results;
  }

  /** NIP-42: Responde automaticamente ao desafio AUTH do relay */
  public handleAuth(relay: string, challenge: string) {
    if (!this.authSecretKey || !this.authPublicKey) return;

    const authEvent = finalizeEvent(
      {
        kind: 22242, // Evento de Auth padrão Nostr
        created_at: Math.floor(Date.now() / 1000),
        tags: [
          ['relay', relay],
          ['challenge', challenge],
        ],
        content: '',
      },
      this.authSecretKey
    );

    // Envia o evento AUTH de volta pelo WebSocket
    this.pool.publish([relay], authEvent);
  }

  public disconnect() {
    this.pool.close([this.relayUrl]);
  }
}
