#include "llm_agent.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/syscall.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <time.h>
#include <stdarg.h>
#include <errno.h>

/* ============================================================================
 * Integração com llama.cpp (via dlopen ou link estático)
 * ============================================================================ */

/* --- AQUI VOCÊ DEVE INCLUIR A BIBLIOTECA llama.cpp --- */
/* Para prototipagem, usamos stubs que simulam inferência. */
/* Substitua pelos cabeçalhos reais do llama.cpp se estiver usando. */

typedef void* llama_model_ptr;
typedef void* llama_context_ptr;

static llama_model_ptr g_model = NULL;
static llama_context_ptr g_ctx = NULL;
static int g_llm_initialized = 0;

/* Stubs para simular llama.cpp (substituir pelas chamadas reais) */
static llama_model_ptr llama_load_model_from_memfd(int fd) {
    (void)fd;
    return (llama_model_ptr)1; /* placeholder */
}

static llama_context_ptr llama_new_context_with_model(llama_model_ptr model) {
    (void)model;
    return (llama_context_ptr)1;
}

static int llama_completion(llama_context_ptr ctx, const char *prompt, char *out, size_t out_len) {
    (void)ctx;
    /* Simula uma resposta genérica */
    snprintf(out, out_len, "Resposta simulada para: %s", prompt);
    return 0;
}

static void llama_free_context(llama_context_ptr ctx) { (void)ctx; }
static void llama_free_model(llama_model_ptr model) { (void)model; }

/* ============================================================================
 * Estado Interno do Agente LLM
 * ============================================================================ */

static LLMState g_llm_state = {0};
static double g_temperature = 0.7;
static int g_top_k = 40;
static double g_top_p = 0.9;

/* Memória de contexto: armazena os últimos N tokens/prompts (simplificado) */
#define MAX_CONTEXT_HISTORY 10
static char *g_context_history[MAX_CONTEXT_HISTORY] = {0};
static size_t g_context_count = 0;

/* ============================================================================
 * Implementação das Funções
 * ============================================================================ */

int llm_init(const uint8_t *model_data, size_t model_len) {
    if (g_llm_initialized) return 0;
    /* Carrega o modelo via memfd */
    int fd = syscall(SYS_memfd_create, "llm_model", MFD_CLOEXEC);
    if (fd < 0) {
        perror("llm_init: memfd_create");
        return -1;
    }
    if (write(fd, model_data, model_len) != (ssize_t)model_len) {
        perror("llm_init: write");
        close(fd);
        return -1;
    }
    /* Sealing opcional */
    fcntl(fd, F_ADD_SEALS, F_SEAL_SEAL | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_WRITE);

    /* Carrega modelo a partir do descritor */
    g_model = llama_load_model_from_memfd(fd);
    close(fd);
    if (!g_model) {
        fprintf(stderr, "llm_init: falha ao carregar modelo\n");
        return -1;
    }
    g_ctx = llama_new_context_with_model(g_model);
    if (!g_ctx) {
        fprintf(stderr, "llm_init: falha ao criar contexto\n");
        llama_free_model(g_model);
        g_model = NULL;
        return -1;
    }

    /* Inicializa estado */
    memset(&g_llm_state, 0, sizeof(g_llm_state));
    g_llm_state.context_tokens = 0;
    g_context_count = 0;
    g_llm_initialized = 1;

    fprintf(stderr, "✅ LLM Agent inicializado com modelo de %zu bytes\n", model_len);
    return 0;
}

void llm_shutdown(void) {
    if (g_ctx) {
        llama_free_context(g_ctx);
        g_ctx = NULL;
    }
    if (g_model) {
        llama_free_model(g_model);
        g_model = NULL;
    }
    for (size_t i = 0; i < g_context_count; i++) {
        free(g_context_history[i]);
        g_context_history[i] = NULL;
    }
    g_context_count = 0;
    g_llm_initialized = 0;
    fprintf(stderr, "🛑 LLM Agent finalizado\n");
}

/* --- Geração de Resposta --- */
int llm_generate(const char *prompt, size_t prompt_len, LLMInteraction *out) {
    if (!g_llm_initialized || !g_ctx) {
        fprintf(stderr, "llm_generate: LLM não inicializado\n");
        return -1;
    }
    if (!out) return -1;

    /* Copia o prompt para o histórico (memória de contexto) */
    if (g_context_count < MAX_CONTEXT_HISTORY) {
        g_context_history[g_context_count] = strdup(prompt);
        g_context_count++;
    } else {
        /* FIFO: remove o mais antigo */
        free(g_context_history[0]);
        for (size_t i = 1; i < g_context_count; i++) {
            g_context_history[i-1] = g_context_history[i];
        }
        g_context_history[g_context_count-1] = strdup(prompt);
    }
    g_llm_state.context_tokens += prompt_len / 4; /* aproximação: 1 token ~4 chars */

    /* Aplica os parâmetros de amostragem */
    llama_completion(g_ctx, prompt, (char*)out->response_hash, 32); /* stub */

    /* Gera resposta simulada (substituir pela chamada real) */
    char response[1024] = {0};
    llama_completion(g_ctx, prompt, response, sizeof(response));

    /* Calcula hashes */
    sha256((const uint8_t*)prompt, prompt_len, out->prompt_hash);
    sha256((const uint8_t*)response, strlen(response), out->response_hash);

    /* Preenche outros campos */
    out->temperature = g_temperature;
    out->top_k = g_top_k;
    out->top_p = g_top_p;

    /* Gera VRF (usando a função existente da Cathedral) */
    vrf_eval(&g_identity.private_key, &g_identity.public_key,
             (const uint8_t*)prompt, prompt_len, &out->vrf_output);

    /* Assinatura: para simplificar, usamos a função de assinatura Schnorr já existente */
    /* (seria melhor usar a função de assinatura da Cathedral) */

    fprintf(stderr, "💬 LLM gerou resposta para prompt de %zu bytes\n", prompt_len);
    return 0;
}

void llm_set_sampling(double temperature, int top_k, double top_p) {
    g_temperature = temperature;
    g_top_k = top_k;
    g_top_p = top_p;
    fprintf(stderr, "🎛️  Parâmetros de amostragem: T=%.2f, k=%d, p=%.2f\n",
            temperature, top_k, top_p);
}

size_t llm_get_context_tokens(void) {
    return g_llm_state.context_tokens;
}

void llm_compress_context(void) {
    /* Remove metade do histórico (esquecimento seletivo) */
    size_t to_keep = MAX_CONTEXT_HISTORY / 2;
    for (size_t i = to_keep; i < g_context_count; i++) {
        free(g_context_history[i]);
        g_context_history[i] = NULL;
    }
    g_context_count = to_keep;
    /* Recalcula tokens aproximados */
    size_t new_tokens = 0;
    for (size_t i = 0; i < g_context_count; i++) {
        new_tokens += strlen(g_context_history[i]) / 4;
    }
    g_llm_state.context_tokens = new_tokens;
    fprintf(stderr, "🧹 Contexto comprimido para %zu prompts (%zu tokens)\n",
            g_context_count, g_llm_state.context_tokens);
}
