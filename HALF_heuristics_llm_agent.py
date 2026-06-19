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
from typing import Any, Dict, List

from base_agent import BaseAgent, STOPWORDS
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
        short_lyrics = " ".join(lyrics.split()[:300])

        prompt = (
            "Você é um jogador em um jogo de associação entre dicas e músicas\n"
            "Você receberá um trecho de uma música utilize ele para gerar um dica para a música poder ser adivinhada com facilidade"
            "Você deve maximixar a qualidade da dica para que a música possa ser adivinhada apenas pela dica"
            "Não é permitido utilizar todas as palavra da letra ou trecho exato da música utilize sinônimos simples ou apenas 2 palavras no máximo, da letra da música "
            "que possam ser adivinhados de forma fácil por outras pessoas"
            f"Use no maximo {max_words} palavras.\n"
            "A dica não precisa e é recomendado não ser uma frase coesa, é ideal que seja apenas palavras chaves soltas quando essa for uma boa dica"
            "A sua saída deve seguir o seguinte formato:"
            "Dica: <<<Sua dica>>> \n\n"
            f"Letra:\n{short_lyrics}\n\n"
        )

        raw = await self.llm_generate(
            prompt,
            max_tokens=200,
            temperature=0.6,
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

        # Heurística: se alguma carta tiver >=3 palavras exatas da dica na letra,
        # escolhe a de maior pontuação sem chamar a LLM.
        best_score, best_idx = 0, -1
        for idx, card in enumerate(self.hand):
            lyrics_words = self._normalize_words(card.get("lyrics", ""))
            score = len(clue_words.intersection(lyrics_words))
            if score > best_score:
                best_score, best_idx = score, idx
        if best_score >= 3:
            return {"chosen_card": self.hand[best_idx]}

        prompt = (
            "Você é um jogador em um jogo de associação entre dicas e músicas\n"
            "Você receberá uma dica e uma lista de músicas contendo titulo:letra"
            "escolha a música mais compatível com dica"
            "A lista deve utilizar os títulos como forma de identificação"
            "Justifique as 2 primeiras posições com no máximo 30 palavras e apenas no final da sua resposta coloque a lista"
            "Você deve responder exatamente da seguinte forma, contendo apenas e exatamente uma lista nesse formato sem qualquer outro marcador markdown exceto pela explicação:"
            "response: [lista de títulos ordenados de acordo com a compatibilidade com a dica]"
            f"Dica:\n{clean_clue}\n\n"
            f"Lista de músicas com suas letras: {self.hand}"
        )

        raw = await self.llm_generate(
            prompt,
            max_tokens=1000,
            temperature=0.2,
            stop=["\n\n", "\nResposta:", "\nAnswer:", "###"],
        )

        chosen_idx = self._sanitize_card_choice(raw)
        return {"chosen_card": self.hand[chosen_idx]}

    @tool()
    async def vote(self, clue: str, options: List[Dict[str, Any]], my_chosen_card: Dict[str, Any]) -> Dict[str, Any]:

        clue_words = self._normalize_words(clue)
        clean_clue = [x for x in clue_words]

        my_idx = next((i for i, opt in enumerate(options) if opt["id"] == my_chosen_card["id"]), -1)

        # Heurística roda primeiro para determinar sua escolha
        scored: List[tuple[int, int]] = []
        for idx, option in enumerate(options):
            if idx == my_idx:
                continue
            first_300 = " ".join(option.get("lyrics", "").split()[:300])
            lyrics_words = self._normalize_words(first_300) - STOPWORDS
            score = len(clue_words.intersection(lyrics_words))
            scored.append((score, idx))

        scored.sort(reverse=True)

        heuristic_pick: int | None = scored[0][1] if scored else None

        # LLM recebe opções sem my_chosen_card e sem a carta da heurística
        excluded_ids = {my_chosen_card.get("id")}
        if heuristic_pick is not None:
            excluded_ids.add(options[heuristic_pick]["id"])

        llm_options = [opt for opt in options if opt["id"] not in excluded_ids]
        options_str = "\n".join(
            f"{idx+1}. {option.get('title', '')}: {option.get('lyrics', '')}"
            for idx, option in enumerate(llm_options)
        )

        prompt = (
            "Você é um jogador em um jogo de associação entre dicas e músicas\n"
            "Você receberá uma dica e uma lista de cartas que contém títulos e letras de músicas"
            "você deve verificar cada música e escolher a música mais provável de corresponder a dica"
            "As músicas estão numeradas a partir de 1, utilize esses números para escolher."
            f"Dica:\n{clean_clue}\n\n"
            f"Lista de músicas com suas letras: {options_str}\n\n"
            "Utilize o seu voto com confiabilidade, verifique as letras de músicas que possuem palavras em comum isso pode ser um indício "
            "Utilize seu voto sem com criatividade para tentar acertar a música."
            "Responda exatamente da seguinte forma sem qualquer outro marcador markdown ou explicação a mais:"
            "response: [número da música escolhida]"
        )

        raw = await self.llm_generate(
            prompt,
            max_tokens=50,
            temperature=0.1,
            stop=["\n\n", "\nResposta:", "\nAnswer:", "###"],
        )

        # mapeia índice de volta para options original
        llm_to_orig = {fi: next(oi for oi, opt in enumerate(options) if opt["id"] == card["id"])
                       for fi, card in enumerate(llm_options)}
        llm_votes_filtered = self.sanitize_votes(raw, n_options=len(llm_options))
        llm_clean_votes = [llm_to_orig[i] for i in llm_votes_filtered if i in llm_to_orig]

        # heurística tem prioridade; LLM preenche a segunda posição
        clean_votes: List[int] = []
        if heuristic_pick is not None:
            clean_votes.append(heuristic_pick)
        clean_votes.extend(llm_clean_votes)

        # fallback com voto aleatório
        if len(clean_votes) < 2:
            for idx in range(len(options)):
                if idx != my_idx and idx not in clean_votes:
                    clean_votes.append(idx)
                if len(clean_votes) >= 2:
                    break

        return {"votes": clean_votes[:2]}


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
