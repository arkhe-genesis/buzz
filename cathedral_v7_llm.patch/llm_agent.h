#ifndef LLM_AGENT_H
#define LLM_AGENT_H

#include <stdint.h>
#include <stddef.h>

/* ============================================================================
 * Estruturas para Interações LLM
 * ============================================================================ */

typedef struct {
    uint8_t prompt_hash[32];
    uint8_t response_hash[32];
    uint8_t signature[64];      /* Schnorr (ou Ed25519) sobre prompt_hash||response_hash */
    uint8_t vrf_output[32];     /* VRF do prompt (para aleatoriedade verificável) */
    double temperature;          /* Parâmetros de amostragem usados */
    int top_k;
    double top_p;
} LLMInteraction;

typedef struct {
    uint8_t model_hash[32];     /* Hash do modelo carregado (para atestar versão) */
    uint8_t context_hash[32];   /* Hash do estado do contexto (memória) */
    size_t context_tokens;      /* Número de tokens no contexto atual */
    LLMInteraction last_interaction;
} LLMState;

/* ============================================================================
 * Funções Principais
 * ============================================================================ */

/* Inicializa o subsistema LLM: carrega modelo (via memfd) ou conecta à API */
int llm_init(const uint8_t *model_data, size_t model_len);

/* Gera uma resposta para um prompt, atualiza o estado e retorna a interação */
int llm_generate(const char *prompt, size_t prompt_len, LLMInteraction *out);

/* Define os parâmetros de amostragem (temperatura, top-k, top-p) */
void llm_set_sampling(double temperature, int top_k, double top_p);

/* Obtém o número de tokens no contexto atual (para Bekenstein) */
size_t llm_get_context_tokens(void);

/* Comprime/reseta o contexto (esquecimento seletivo) */
void llm_compress_context(void);

/* Libera recursos do subsistema LLM */
void llm_shutdown(void);

#endif /* LLM_AGENT_H */
