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
            "Você deve gerar uma explicação para a dica que vai dar como resposta e apenas no final escrever a"
            " dica real com o indicador Dica: <<<Sua dica>>> \n\n"
            f"Letra:\n{short_lyrics}\n\n"
        )

        raw = await self.llm_generate(
            prompt,
            max_tokens=400,
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
        # Estratégia simples:
        # tenta votar nas duas opções com maior interesecao entre dica e título.
        # Se n der certo, vota nas duas primeiras que não forem a própria carta.
        my_idx = next(i for i, option in enumerate(options) if option["id"] == my_chosen_card["id"])
        clue_words = self._normalize_words(clue)

        scored: List[tuple[int, int]] = []
        for idx, option in enumerate(options):
            if idx == my_idx:
                continue
            title_words = self._normalize_words(option.get("title", ""))
            score = len(clue_words.intersection(title_words))
            scored.append((score, idx))

        scored.sort(reverse=True)

        votes: List[int] = []
        for _, idx in scored:
            if idx != my_idx and idx not in votes:
                votes.append(idx)
            if len(votes) == 2:
                break

        if len(votes) < 2:
            for idx in range(len(options)):
                if idx != my_idx and idx not in votes:
                    votes.append(idx)
                if len(votes) == 2:
                    break

        return {"votes": votes[:2]}

    

    def _normalize_words(self, text: str) -> set[str]:
        # normaliza palavras no texto e devolve como um conjunto
        cleaned = []
        for token in text.lower().split():
            token = "".join(ch for ch in token if ch.isalnum())
            if token:
                cleaned.append(token)
        return set(cleaned)


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
