# Patch Completo: Integração de LLM à Cathedral Engine v7.0

## Estrutura do Patch

```
cathedral_v7_llm.patch
├── llm_agent.h          # Declarações das novas funções/estruturas
├── llm_agent.c          # Implementação das funções LLM
├── cathedral_v7.c.diff  # Modificações no main loop e integração
└── README.md            # Instruções de compilação e uso
```

## Instruções de Compilação e Uso

1. Coloque os arquivos no mesmo diretório:
   - `cathedral_v7.c` (com as modificações acima)
   - `llm_agent.h`
   - `llm_agent.c`

2. Compile com suporte a llama.cpp (se quiser real) ou com os stubs:
```bash
gcc -static -O2 -fno-stack-protector -no-pie -o cathedral \
    cathedral_v7.c llm_agent.c -lm
```

3. Execute com um modelo LLM (ex: um arquivo .gguf):
```bash
./cathedral --llm-model /caminho/para/modelo.gguf --verbose
```

4. Para interagir, digite prompts no stdin e pressione Enter:
```
Digite seu prompt: O que é a Cathedral Engine?
💬 Resposta gerada...
```