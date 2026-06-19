#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analisa os N logs mais recentes de Nota Secreta e gera estatísticas."""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


LOGS_DIR = Path(__file__).parent / "logs"
RESULTS_DIR = Path(__file__).parent / "results"


def load_recent_logs(num_logs: int) -> Tuple[List[Dict[str, Any]], List[str]]:
    log_files = sorted(
        LOGS_DIR.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    selected = log_files[:num_logs]
    logs = []
    for path in selected:
        with path.open("r", encoding="utf-8") as f:
            logs.append(json.load(f))
    return logs, [p.name for p in selected]


def agent_alias(name: str) -> str:
    """Remove o sufixo numérico de posição (_1, _2, …) do nome do agente."""
    return re.sub(r"_\d+$", "", name)


def analyze(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    num_logs = len(logs)
    total_rounds_all = 0

    # Acumuladores por alias de agente
    alias_type: Dict[str, str] = {}       # alias → tipo (strategic/random)
    alias_wins: Dict[str, int] = {}
    alias_vote_hits: Dict[str, int] = {}
    alias_vote_misses: Dict[str, int] = {}
    alias_total_points: Dict[str, float] = {}
    alias_point_slots: Dict[str, int] = {}
    alias_narrator_points: Dict[str, float] = {}
    alias_narrator_slots: Dict[str, int] = {}

    def ensure(alias: str, atype: str) -> None:
        alias_type[alias] = atype
        for d in (alias_wins, alias_vote_hits, alias_vote_misses,
                  alias_total_points, alias_point_slots,
                  alias_narrator_points, alias_narrator_slots):
            d.setdefault(alias, 0)

    for game in logs:
        agents: Dict[int, Dict[str, Any]] = {int(a["id"]): a for a in game["agents"]}

        for agent in agents.values():
            ensure(agent_alias(agent["name"]), agent["type"])

        winner_id = game.get("winner")
        if winner_id is not None:
            winner_alias = agent_alias(agents[int(winner_id)]["name"])
            alias_wins[winner_alias] += 1

        rounds = game.get("rounds", [])
        total_rounds_all += len(rounds)

        for rnd in rounds:
            narrador_id = int(rnd["narrador"])
            narrador_option = int(rnd["narrador_option"])
            scores = rnd.get("scores", [])

            for vote_info in rnd.get("votes_by_agent", []):
                agent_id = int(vote_info["agent"])
                alias = agent_alias(agents[agent_id]["name"])

                if agent_id < len(scores):
                    alias_total_points[alias] += scores[agent_id]
                    alias_point_slots[alias] += 1

                if agent_id == narrador_id:
                    if agent_id < len(scores):
                        alias_narrator_points[alias] += scores[agent_id]
                        alias_narrator_slots[alias] += 1
                    continue

                if narrador_option in vote_info.get("voted_options", []):
                    alias_vote_hits[alias] += 1
                else:
                    alias_vote_misses[alias] += 1

    avg_rounds = total_rounds_all / num_logs if num_logs else 0

    global_hits = sum(alias_vote_hits.values())
    global_misses = sum(alias_vote_misses.values())
    global_votes = global_hits + global_misses
    global_hit_rate = global_hits / global_votes if global_votes else 0

    by_alias: Dict[str, Any] = {}
    all_aliases = sorted(
        set(alias_wins) | set(alias_vote_hits) | set(alias_vote_misses),
        key=lambda a: (alias_type.get(a, "z") != "strategic", a),
    )
    for alias in all_aliases:
        votes = alias_vote_hits[alias] + alias_vote_misses[alias]
        hit_rate = alias_vote_hits[alias] / votes if votes else 0
        slots = alias_point_slots[alias]
        avg_pts = alias_total_points[alias] / slots if slots else 0
        narrator_slots = alias_narrator_slots[alias]
        avg_pts_as_narrator = alias_narrator_points[alias] / narrator_slots if narrator_slots else 0
        by_alias[alias] = {
            "type": alias_type.get(alias, "unknown"),
            "games_won": alias_wins.get(alias, 0),
            "win_rate": round(alias_wins.get(alias, 0) / num_logs, 4) if num_logs else 0,
            "vote_hits": alias_vote_hits.get(alias, 0),
            "vote_misses": alias_vote_misses.get(alias, 0),
            "hit_rate": round(hit_rate, 4),
            "avg_points_per_round": round(avg_pts, 4),
            "avg_points_as_narrator": round(avg_pts_as_narrator, 4),
        }

    return {
        "num_logs": num_logs,
        "avg_rounds_per_game": round(avg_rounds, 2),
        "vote_hits_total": global_hits,
        "vote_misses_total": global_misses,
        "hit_rate_global": round(global_hit_rate, 4),
        "by_agent": by_alias,
    }


def print_results(results: Dict[str, Any], log_names: List[str]) -> None:
    W = 58
    SEP = "=" * W
    sep = "-" * W

    print()
    print(SEP)
    print("  ANALISE DE LOGS  —  NOTA SECRETA")
    print(SEP)
    print(f"  Logs analisados       : {results['num_logs']}")
    print(f"  Media de rodadas/jogo : {results['avg_rounds_per_game']:.1f}")
    print()
    print("  Arquivos analisados:")
    for name in log_names:
        print(f"    • {name}")

    print()
    print(sep)
    print("  VOTOS NA MUSICA CORRETA  (global)")
    print(sep)
    hits = results["vote_hits_total"]
    misses = results["vote_misses_total"]
    total = hits + misses
    print(f"  Acertos       : {hits:>5}  ({hits / total * 100:.1f}%)" if total else "  Acertos  : 0")
    print(f"  Erros         : {misses:>5}  ({misses / total * 100:.1f}%)" if total else "  Erros    : 0")
    print(f"  Hit rate      : {results['hit_rate_global'] * 100:.1f}%")

    print()
    print(sep)
    print("  ESTATISTICAS POR AGENTE")
    print(sep)

    for alias, stats in results["by_agent"].items():
        print(f"  [{alias}]  ({stats['type']})")
        print(f"    Vitorias          : {stats['games_won']}  (win rate {stats['win_rate'] * 100:.1f}%)")
        print(f"    Acertos de voto   : {stats['vote_hits']}")
        print(f"    Erros de voto     : {stats['vote_misses']}")
        print(f"    Hit rate          : {stats['hit_rate'] * 100:.1f}%")
        print(f"    Media pts/rodada  : {stats['avg_points_per_round']:.2f}")
        print(f"    Media pts/narrador: {stats['avg_points_as_narrator']:.2f}")
        print()

    print(SEP)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analisa os N logs mais recentes de partidas de Nota Secreta."
    )
    parser.add_argument(
        "-n", "--num_logs",
        type=int,
        default=5,
        metavar="N",
        help="Numero de logs mais recentes a analisar (default: 5)",
    )
    args = parser.parse_args()

    logs, log_names = load_recent_logs(args.num_logs)
    if not logs:
        print(f"Nenhum log encontrado em {LOGS_DIR}")
        return

    results = analyze(logs)

    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"analysis_{timestamp}.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print_results(results, log_names)
    print(f"  Resultado salvo em: {output_path}")
    print()


if __name__ == "__main__":
    main()
