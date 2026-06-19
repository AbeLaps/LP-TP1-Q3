from __future__ import annotations

"""Agente estratégico MEGA simples.
Marco Cristo, 2026

Objetivo desta versão:
- servir como ponto de partida;
- manter a interface esperada pela infraestrutura;
- ser funcional, para vcs terem um exemplo que roda.

Características:
- escolhe a carta do narrador por uma heurística muito simples;
- gera dica com a LLM, mas com prompt beeeem básico;
- escolhe carta e votos com regras ingênuas;
- não tenta otimizar de verdade para vencer o baseline aleatório.
"""

import argparse
import re
import random
from typing import Any, Dict, List

from base_agent import BaseAgent
from fasta2a import A2AApp, tool

app = A2AApp(name="LLMAgent")


class LLMAgent(BaseAgent):
    def __init__(self, name: str, llm_url: str):
        super().__init__(name=name, llm_url=llm_url, request_timeout=60.0)

    @tool()
    async def receive_hand(self, hand: List[Dict[str, Any]]) -> Dict[str, Any]:
        self.hand = list(hand)
        return {"status": "ok", "hand_size": len(self.hand)}

    @tool()
    async def choose_card(self) -> Dict[str, Any]:
        if not self.hand:
            raise RuntimeError("Hand is empty")
        
        prompt = (
            "Você é um jogador em um jogo de associação entre dicas e músicas\n"
            "Você tem a tarefa de escolher uma música tal que a música seja complexa o suficiente para"
            "que seja possível criar uma dica que não seja óbvia para a música e que não contenha nenhuma"
            "palavra idêntica a letra da música"
            f"Músicas disponíveis no formato título:Letra: {self.hand}"
            "A sua resposta deve ser APENAS e exatamente o título da música de forma cru sem qualquer"
            "marcador"
        )

        raw = await self.llm_generate(
            prompt,
            max_tokens=200,
            temperature=0.3,
            stop=["\n\n", "\nResposta:", "\nAnswer:", "###"],
        )

        

        chosen_idx = self._sanitize_card_choice(raw)
        return {"chosen_card": self.hand[chosen_idx]}

    @tool()
    async def send_clue(self, lyrics: str, max_words: int = 6) -> Dict[str, Any]:
        # Prompt alterado, teste com reason antes da dica final
        short_lyrics = " ".join(lyrics.split()[:100]) + "$$$" + " ".join(lyrics.split()[-30:])

        prompt = (
            "Você é um jogador em um jogo de associação entre dicas e músicas\n"
            "Você receberá o início e o final de uma letra de uma música separadas pelo separador '$$$', "
            "utilize ela para gerar um dica para a música"
            "Para a dica priorize utilizar o final da música de forma a conter também o início parcialmente"
            "Você deve maximixar a qualidade da dica para que a música possa ser adivinhada apenas pela dica"
            "Evite ao máximo utilizar qualquer palavra da letra ou trecho exato da música"
            f"Use no maximo {max_words} palavras.\n"
            "A dica não precisa e é recomendado não ser uma frase correta, é ideal que seja apenas palavras chaves soltas"
            "Você deve gerar uma explicação curta para a dica que vai dar como resposta e apenas no final escrever a"
            " dica real com o indicador Dica: <<<Sua dica>>> \n\n"
            f"Letra:\n{short_lyrics}\n\n"
        )

        raw = await self.llm_generate(
            prompt,
            max_tokens=2000,
            temperature=0.3,
            stop=["\n\n", "\nResposta:", "\nAnswer:", "###"],
        )

        extracted_clue = self._extract_clue_from_response(raw)
        clue = self._sanitize_clue(extracted_clue, max_words=max_words, lyrics=lyrics)

        if not clue:
            clue = "coisa estranha"

        return {"clue": clue}

    @tool()
    async def select_card_by_clue(self, clue: str) -> Dict[str, Any]:
        if not self.hand:
            raise RuntimeError("Hand is empty")

        clue_words = self._normalize_words(clue)
        clean_clue = [x for x in clue_words]

        prompt = (
            "Você é um jogador em um jogo de associação entre dicas e músicas\n"
            "Você receberá uma dica e uma lista de músicas contendo titulo:letra"
            "Ordene essa lista das músicas de forma decrescente partindo da música que tem mais chance de gerar essa dica"
            "A lista deve utilizar os títulos como forma de identificação"
            "Você deve responder exatamente da seguinte forma, contendo apenas e exatamente uma lista nesse formato sem qualquer outro marcador markdown:"
            "response: [lista de títulos ordenados]"
            f"Dica:\n{clean_clue}\n\n"
            f"Lista de músicas com suas letras: {self.hand}"
        )

        raw = await self.llm_generate(
            prompt,
            max_tokens=200,
            temperature=0.3,
            stop=["\n\n", "\nResposta:", "\nAnswer:", "###"],
        )

        chosen_idx = self._sanitize_card_choice(raw)
        return {"chosen_card": self.hand[chosen_idx]}

    @tool()
    async def vote(self, clue: str, options: List[Dict[str, Any]], my_chosen_card: Dict[str, Any]) -> Dict[str, Any]:
        
        clue_words = self._normalize_words(clue)
        clean_clue = [x for x in clue_words]

        # retirar a chosen card das opções
        options = [n for n in options if n['id'] != my_chosen_card.get('id')] 
        options_str = "\n".join(f"{idx+1}. {option.get('title', '')}: {option.get('lyrics', '')}" for idx, option in enumerate(options))

        prompt = (
            "Você é um jogador em um jogo de associação entre dicas e músicas\n"
            "Você receberá um dica e 5 cartas que contém títulos e letras de músicas"
            "você deve verificar cada música e escolher as duas que são mais prováveis de gerar essa dica"
            "As músicas estão no formato título:letra e estão numeradas de 1 a 5, utilize esses números para" 
            "escolher as cartas."
            f"Dica:\n{clean_clue}\n\n"
            f"Lista de músicas com suas letras: {options_str}\n\n"
            "Responda exatamente da seguinte forma sem qualquer outro marcador markdown ou explicação a mais:"
            "response: [número da primeira escolha, número da segunda escolha]"
        )

        raw = await self.llm_generate(
            prompt,
            max_tokens=200,
            temperature=0.3,
            stop=["\n\n", "\nResposta:", "\nAnswer:", "###"],
        )

        clean_votes = sanitize_votes(raw)

        # fallback com voto aleatório
        if len(clean_votes) < 2:
            for _ in range(len(options)-1):
                if len(clean_votes) >= 2:
                    break
                else:
                    clean_votes.append(random.randint(0, len(options)))

        return {"votes": clean_votes[:2]}

    def _extract_clue_from_response(self, raw: str) -> str:
        """Extrai somente o texto após o indicador 'Dica:' na resposta da LLM.

        Formatos aceitos (em ordem de prioridade):
          1. Dica: <<<texto>>>   — extrai apenas o conteúdo entre <<< e >>>
          2. Dica: texto         — extrai tudo após 'Dica:' até o fim da linha
        Fallback: retorna o raw completo.
        """
        match = re.search(r'[Dd]ica\s*:\s*<<<(.+?)>>>', raw)
        if match:
            return match.group(1).strip()

        match = re.search(r'[Dd]ica\s*:\s*(.+)', raw)
        if match:
            return match.group(1).strip()

        return raw.strip()

    def _sanitize_card_choice(self, raw: str) -> int:
        """Extrai a lista `response: [título1, título2, ...]` da resposta da LLM
        e retorna o índice em self.hand do título mais bem ranqueado."""
        match = re.search(r'response\s*:\s*\[([^\]]+)\]', raw, re.IGNORECASE)
        if not match:
            match = re.search(r'\[([^\]]+)\]', raw)

        if match:
            raw_items = match.group(1).split(',')
            items = [item.strip().strip("\"'") for item in raw_items if item.strip()]

            # 1ª passagem: match exato por palavras normalizadas
            for item in items:
                item_words = self._normalize_words(item)
                if not item_words:
                    continue
                for idx, song in enumerate(self.hand):
                    if item_words == self._normalize_words(song.get("title", "")):
                        return idx

            # 2ª passagem: match parcial (um conjunto é subconjunto do outro)
            for item in items:
                item_words = self._normalize_words(item)
                if not item_words:
                    continue
                for idx, song in enumerate(self.hand):
                    title_words = self._normalize_words(song.get("title", ""))
                    if item_words <= title_words or title_words <= item_words:
                        return idx

        return random.randrange(len(self.hand))

    def _normalize_words(self, text: str) -> set[str]:
        # normaliza palavras no texto e devolve como um conjunto
        cleaned = []
        for token in text.lower().split():
            token = "".join(ch for ch in token if ch.isalnum())
            if token:
                cleaned.append(token)
        return set(cleaned)


def sanitize_votes(raw: str, n_options: int = 5) -> List[int]:
    """Extrai índices de voto (base 0) da resposta da LLM.

    Formato esperado: response: [1, 3]  (base 1)
    Retorna lista de índices base-0 sem duplicatas, ou lista vazia se não
    for possível parsear — o fallback heurístico em vote() cobre esse caso.
    """
    match = re.search(r'response\s*:\s*\[([^\]]+)\]', raw, re.IGNORECASE)
    if not match:
        match = re.search(r'\[([^\]]+)\]', raw)
    if not match:
        return []

    indices: List[int] = []
    for part in match.group(1).split(','):
        num = re.search(r'\d+', part)
        if num:
            idx = int(num.group()) - 1
            if 0 <= idx < n_options and idx not in indices:
                indices.append(idx)
    return indices


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("game_master_url")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--llm-url", default="http://127.0.0.1:9000")
    parser.add_argument("--name", default=None)
    args = parser.parse_args()

    agent = LLMAgent(name=args.name or f"LLMAgent_{args.port}", llm_url=args.llm_url)
    app.register(agent)
    app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
