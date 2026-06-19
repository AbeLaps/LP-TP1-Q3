# Trabalho Prático 2 — Linguagens de Programação 2026/1
## Nota Secreta — Agente Estratégico com Heurísticas e LLM

Este projeto implementa um agente estratégico para o jogo *Nota Secreta*, inspirado no Dixit. É uma simulação multiagente onde cada jogador é um programa autônomo que possui uma mão de cartas de músicas brasileiras. A cada rodada, um agente assume o papel de **narrador**: escolhe uma de suas cartas, gera uma **dica com no máximo 6 palavras** baseada na letra, e os demais agentes tentam adivinhar qual música é a do narrador, votando entre todas as cartas jogadas naquela rodada.

O jogo termina quando algum agente atinge a **pontuação-alvo** (padrão: 30 pontos).

---

## Integrantes do Grupo

- Abel Andrade Prazeres dos Santos
- Bruna de Souza Brasil
- Gabriel Gregório dos Santos Vitor

---

## Como Executar

### Setup inicial

Crie um ambiente virtual:

```bash
python3 -m venv venv
source venv/bin/activate
```

Instale as dependências:

```bash
python3 -m pip install -r requirements.txt
```

Instale o modelo GGUF:

```bash
wget https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/main/Phi-3.5-mini-instruct-Q4_K_M.gguf
```

### Rodar o jogo

Existem 2 configurações de comportamento dos agentes:

- **Modo mock** (sem LLM real, útil para testar a arquitetura):
```bash
python3 run_game.py --force-mock
```

- **Com modelo GGUF real**:
```bash
python3 run_game.py --model <path para o modelo .gguf>
```

#### Configuração de quais agentes jogam

- Com todos os agentes estratégicos:
```bash
python3 run_game.py --all-strategic --force-mock
```

- Para personalização manual dos agentes, consulte o README.md oficial do trabalho.

---

## Exemplo de Saída Esperada

A seguir, um exemplo real de duas rodadas completas extraídas de um log de partida com 6 agentes estratégicos.

### Rodada 1 — Narrador: BASEllm_agent_1_1

| Campo | Valor |
|---|---|
| Narrador | BASEllm_agent_1_1 |
| Música do narrador | *Além do Horizonte* — Roberto Carlos |
| Dica gerada | `memória tempo cidade` |

**Cartas na mesa (embaralhadas):**

| Opção | Agente | Música | Artista |
|---|---|---|---|
| 0 | llm_agent_2 | Festa | Ivete Sangalo |
| 1 | llm_agent_3 | Já Sei Namorar | Tribalistas |
| 2 | BASEllm_agent_3_5 | Bate Coração | Elba Ramalho |
| **3** | **BASEllm_agent_1_1** | **Além do Horizonte** *(narrador)* | Roberto Carlos |
| 4 | BASEllm_agent_4_6 | Eu Sei Que Vou Te Amar | Vinicius de Moraes |
| 5 | BASEllm_agent_2_4 | O Caderno | Toquinho |

**Votos:**

| Agente votante | Votos (opções escolhidas) |
|---|---|
| llm_agent_2 | 5, 1 |
| llm_agent_3 | 0, 2 |
| BASEllm_agent_2_4 | 4, **3** ✓ |
| BASEllm_agent_3_5 | 5, 4 |
| BASEllm_agent_4_6 | 5, **3** ✓ |

Agentes BASEllm_agent_2_4 e BASEllm_agent_4_6 acertaram a música do narrador (opção 3). Resultado parcial — nem todos acertaram, nem todos erraram. Narrador e acertadores recebem +3.

**Pontuação após a rodada 1:**

| Agente | Pontos da rodada | Acumulado |
|---|---|---|
| BASEllm_agent_1_1 *(narrador)* | +3 | **3** |
| llm_agent_2 | +1 *(1 voto recebido)* | **1** |
| llm_agent_3 | +1 *(1 voto recebido)* | **1** |
| BASEllm_agent_2_4 | +3 *(acerto)* +3 *(3 votos recebidos)* | **6** |
| BASEllm_agent_3_5 | +1 *(1 voto recebido)* | **1** |
| BASEllm_agent_4_6 | +3 *(acerto)* +2 *(2 votos recebidos)* | **5** |

---

### Rodada 2 — Narrador: llm_agent_2

| Campo | Valor |
|---|---|
| Narrador | llm_agent_2 |
| Música do narrador | *Chão de Giz* — Zé Ramalho |
| Dica gerada | `memória tempo cidade` |

**Cartas na mesa (embaralhadas):**

| Opção | Agente | Música | Artista |
|---|---|---|---|
| 0 | llm_agent_3 | Pelados em Santos | Mamonas Assassinas |
| 1 | BASEllm_agent_1_1 | Malandrinha | Francisco Alves |
| 2 | BASEllm_agent_3_5 | Triste Bahia | Caetano Veloso |
| 3 | BASEllm_agent_4_6 | Deslizes | Fagner |
| **4** | **llm_agent_2** | **Chão de Giz** *(narrador)* | Zé Ramalho |
| 5 | BASEllm_agent_2_4 | O Caderno | Toquinho |

**Votos:**

| Agente votante | Votos (opções escolhidas) |
|---|---|
| BASEllm_agent_1_1 | — *(não votou)* |
| llm_agent_3 | 0, 2 |
| BASEllm_agent_2_4 | **4** ✓, 3 |
| BASEllm_agent_3_5 | 5, **4** ✓ |
| BASEllm_agent_4_6 | 5, 3 |

Agentes BASEllm_agent_2_4 e BASEllm_agent_3_5 acertaram a música do narrador (opção 4). Resultado parcial novamente.

**Placar acumulado após rodada 2:**

| Agente | Acumulado |
|---|---|
| BASEllm_agent_1_1 | **3** |
| llm_agent_2 | **4** |
| llm_agent_3 | **2** |
| BASEllm_agent_2_4 | **9** |
| BASEllm_agent_3_5 | **2** |
| BASEllm_agent_4_6 | **8** |

---

## Descrição dos Prompts e Heurísticas Implementadas

O agente estratégico (`llm_agent.py`) combina heurísticas determinísticas com chamadas à LLM para cada fase do jogo.

### `choose_card()` — Escolha da carta para narrar

**Abordagem:** chamada à LLM com prompt orientado à complexidade semântica da letra.

O prompt instrui o modelo a escolher uma música suficientemente complexa para que seja possível criar uma dica ambígua que não contenha nenhuma palavra idêntica à letra. A resposta esperada é apenas o título da música, e `_sanitize_card_choice` extrai o índice correto mesmo quando a LLM não responde de forma exata.

```
Temperatura: 0.3 | max_tokens: 200
Stop: ["\n\n", "\nResposta:", "\nAnswer:", "###"]
```

---

### `send_clue()` — Geração da dica

**Abordagem:** raciocínio guiado por prompt + validação pós-geração.

O prompt solicita que a LLM:
- Utilize apenas os primeiros 300 tokens da letra para gerar a dica;
- Produza uma dica com no máximo `max_words` palavras (padrão: 6);
- Evite trechos literais da letra; use sinônimos e no máximo 2 palavras diretas da música;
- Retorne a resposta no formato `Dica: <<<sua dica>>>`.

A resposta é extraída pelo método `_extract_clue_from_response` (que busca o padrão `Dica: <<<...>>>` ou `Dica: ...`) e depois sanitizada por `_sanitize_clue` da classe base, que remove literais copiados da letra e formata a saída.

```
Temperatura: 0.6 | max_tokens: 200
Stop: ["\n\n", "\nResposta:", "\nAnswer:", "###"]
```

---

### `select_card_by_clue()` — Escolha da carta pela dica (como ouvinte)

**Abordagem:** heurística de interseção de palavras com fallback para a LLM.

1. **Heurística rápida:** normaliza as palavras da dica e de cada letra da mão (removendo pontuação e convertendo para minúsculas). Se alguma carta atingir **3 ou mais palavras em comum** com a dica, ela é escolhida diretamente sem chamar a LLM.

2. **Fallback LLM:** se nenhuma carta ultrapassar o limiar, a LLM recebe a dica e a lista de músicas (título + letra) para ranquear as opções. O prompt pede uma lista ordenada no formato `response: [título1, título2, ...]`, e `_sanitize_card_choice` mapeia o título mais bem ranqueado para o índice correto na mão.

```
Heurística: threshold = 3 palavras em comum
Temperatura LLM: 0.2 | max_tokens: 1000
```

---

### `vote()` — Votação (como ouvinte)

**Abordagem:** heurística com prioridade + LLM para complementar.

1. **Heurística (1º voto):** pontua todas as cartas na mesa (exceto a própria) pelo número de palavras da dica presentes na letra, com remoção de stopwords. A carta com maior pontuação é o primeiro voto.

2. **LLM (2º voto):** recebe as cartas restantes (excluindo a própria carta e a já escolhida pela heurística) e retorna qual delas melhor combina com a dica. O resultado é mapeado de volta para os índices originais das opções.

3. **Fallback determinístico:** se a lista de votos ainda estiver incompleta após a LLM, preenche com as próximas cartas disponíveis em ordem.

A heurística tem sempre prioridade sobre a LLM; a LLM só é consultada para preencher a segunda posição do voto.

```
Temperatura LLM: 0.1 | max_tokens: 200
```

---

## Dificuldades Encontradas e Soluções

### Geração de dicas com dificuldade calibrada

Fazer o modelo gerar uma dica que não fizesse todos os agentes acertarem e nem todos errarem foi simples e não precisou de muito esforço: ajustar a temperatura do prompt de `send_clue` e instruir o modelo a evitar trechos literais da letra já foi suficiente para produzir dicas com grau de ambiguidade adequado, sem precisar de iterações complexas.

### Melhoria do voto — a maior dificuldade

A parte de melhorar o voto foi de **extrema dificuldade**. O principal desafio foi testar a heurística de interseção de palavras e definir o **threshold** de quantas palavras da dica deveriam estar presentes na letra da música para que a escolha fosse confiável o suficiente para dispensar a LLM.

- Valores muito baixos (1 ou 2 palavras) geravam muitos falsos positivos, pois palavras comuns apareciam em diversas letras.
- Valores muito altos tornavam a heurística inútil, pois raramente era ativada.
- O limiar de **3 palavras** foi encontrado empiricamente após múltiplas rodadas de teste, equilibrando precisão e cobertura.

Além disso, a integração entre a heurística (1º voto) e a LLM (2º voto) exigiu cuidado para que os índices das opções fossem mapeados corretamente entre o conjunto filtrado enviado à LLM e o conjunto original de opções do jogo.
