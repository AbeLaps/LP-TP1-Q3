# Resumo do Projeto — Nota Secreta

## O que é o jogo

**Nota Secreta** é um jogo de associação de músicas para **6 agentes** (jogadores autônomos), inspirado em jogos como Dixit. Cada agente possui uma mão de cartas de músicas brasileiras e, a cada rodada, um agente assume o papel de **narrador**: escolhe uma de suas cartas, gera uma **dica com no máximo 6 palavras** baseada na letra, e os demais agentes tentam adivinhar qual música é a do narrador votando entre todas as cartas jogadas naquela rodada.

O jogo termina quando algum agente atinge a **pontuação-alvo** (padrão: 30 pontos).

---

## Fluxo de uma partida

```
run_game.py
   │
   ├─ sobe llm_service.py        ← serviço LLM (real ou mock)
   ├─ sobe game_master.py        ← árbitro da partida
   ├─ sobe llm_agent.py          ← 1 agente estratégico
   ├─ sobe random_agent.py (×5)  ← 5 agentes aleatórios (baseline)
   ├─ registra todos no Game Master
   └─ dispara POST /play  →  partida completa
```

Cada rodada segue este fluxo exato:

1. **choose_card** — narrador escolhe qual música vai jogar.
2. **send_clue** — narrador gera a dica (≤ 6 palavras) com base na letra.
3. **select_card_by_clue** — cada não-narrador escolhe qual das suas músicas mais combina com a dica.
4. As cartas são **embaralhadas** e apresentadas como opções numeradas.
5. **vote** — cada não-narrador vota em **2 opções** (exceto a própria carta).
6. Pontuação é aplicada e as cartas jogadas são **repostas** do baralho.

---

## Regras de pontuação

| Situação | Narrador | Quem acertou | Quem errou |
|---|---|---|---|
| Ninguém acertou OU todos acertaram | 0 | — | +2 |
| Pelo menos um, mas não todos, acertaram | +3 | +3 | 0 |

Na versão completa (padrão), cada não-narrador ainda ganha até **+3 pontos extras** pelo número de votos recebidos na própria carta (outros agentes que "caíram na isca" e votaram na sua música).

---

## Arquitetura do sistema

O projeto usa **dois protocolos** de comunicação:

| Protocolo | Entre quem |
|---|---|
| REST / FastAPI | Agentes ↔ `llm_service.py` |
| A2A / JSON-RPC 2.0 | `game_master.py` ↔ Agentes |

Cada agente é um **servidor HTTP independente** que expõe um endpoint `/rpc`. O Game Master chama as *tools* dos agentes enviando requisições JSON-RPC para esse endpoint.

---

## Descrição de cada arquivo

| Arquivo | Papel |
|---|---|
| `run_game.py` | Orquestrador: sobe todos os serviços, registra agentes e dispara a partida |
| `game_master.py` | Árbitro: distribui cartas, conduz rodadas, aplica pontuação e salva logs |
| `llm_service.py` | Serviço LLM centralizado; suporta modo real (llama-cpp com GGUF) e modo mock |
| `fasta2a.py` | Mini-implementação do protocolo A2A: `A2AApp` e decorador `@tool` |
| `base_agent.py` | Classe base dos agentes: cliente REST do LLM, parsing de respostas, heurísticas de sanitização de dicas |
| `llm_agent.py` | Agente estratégico (a ser modificado pelo aluno): usa LLM para gerar dicas |
| `random_agent.py` | Agente baseline aleatório: escolhas e votos completamente aleatórios |
| `brazilian_songs.csv` | Base de músicas (colunas: `id`, `title`, `artist`, `lyrics`) |
| `render_log_readable.py` | Converte logs JSON em visualização legível no terminal |
| `tests/` | Testes auxiliares |
| `logs/` | Logs JSON de cada partida (salvos automaticamente pelo Game Master) |

---

## O agente estratégico (`llm_agent.py`)

O `LLMAgent` implementa as 5 *tools* exigidas pela infraestrutura:

| Tool | O que faz na implementação atual |
|---|---|
| `receive_hand(hand)` | Armazena a mão recebida |
| `choose_card()` | Escolhe a carta com comprimento de letra mais próximo da mediana da mão |
| `send_clue(lyrics, max_words)` | Envia início + fim da letra para a LLM e sanitiza a resposta |
| `select_card_by_clue(clue)` | Escolhe a carta cujo título tem mais palavras em comum com a dica |
| `vote(clue, options, my_chosen_card)` | Vota nas 2 opções com mais palavras em comum com a dica |

O `BaseAgent` fornece utilitários compartilhados: cliente REST da LLM com cache por hash, parsing robusto de respostas (JSON, números, rankings), sanitização de dicas (remove prefixos, markdown, literais copiados da letra) e fallback quando a LLM retorna resposta inválida.

---

## O serviço LLM (`llm_service.py`)

Expõe um único endpoint `POST /generate` com os parâmetros `prompt`, `max_tokens`, `temperature` e `stop`. Internamente:

- **Modo real**: carrega um modelo GGUF via `llama-cpp-python` (ex.: Phi-3.5-mini).
- **Modo mock**: retorna sempre `"memória tempo cidade"` — útil para testar a infra sem GPU.

A classe `QueueProcessor` usa um `asyncio.Semaphore` para controlar concorrência (padrão: 1 requisição por vez).

---

## Como executar

```bash
# Instalar dependências
python3 -m pip install -r requirements.txt

# Modo mock (testa a arquitetura sem LLM real)
python3 run_game.py --force-mock

# Com modelo GGUF real
python3 run_game.py --model models/Phi-3.5-mini-instruct-Q4_K_M.gguf

# 6 agentes estratégicos (sem aleatórios)
python3 run_game.py --all-strategic --force-mock

# Ler log de uma partida
python3 render_log_readable.py logs/partida_xxx.json
```

---

## Objetivo pedagógico

O foco é construir um **sistema multiagente baseado em LLM** que:

- use a LLM para decisões semânticas (geração de dicas, seleção de cartas);
- lide de forma robusta com respostas imperfeitas da LLM;
- preserve a interface externa esperada pela infraestrutura.

O aluno deve modificar principalmente `llm_agent.py` (e opcionalmente `base_agent.py`), sem quebrar a compatibilidade com o Game Master.

O baseline a ser superado é o `random_agent.py` — vencê-lo sistematicamente já equivale a 1 ponto na avaliação.
