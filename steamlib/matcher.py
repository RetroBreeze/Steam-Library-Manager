from __future__ import annotations

import re
import string
from dataclasses import dataclass

from rapidfuzz import fuzz

from .models import Game

EDITION_SUFFIXES = (
    "deluxe edition",
    "definitive edition",
    "game of the year",
    "remastered",
    "remake",
    "goty",
)


@dataclass(frozen=True)
class Match:
    game: Game
    score: float


def normalize(value: str) -> str:
    table = str.maketrans({char: " " for char in string.punctuation})
    cleaned = value.casefold().translate(table)
    return re.sub(r"\s+", " ", cleaned).strip()


def comparison_forms(value: str) -> set[str]:
    base = normalize(value)
    forms = {base}
    for suffix in EDITION_SUFFIXES:
        suffix_norm = normalize(suffix)
        forms.add(re.sub(rf"\b{re.escape(suffix_norm)}\b", "", base).strip())
    return {form for form in forms if form}


def _numbers(value: str) -> set[str]:
    return set(re.findall(r"\d+", value))


def score_game(query: str, game: Game) -> float:
    query_forms = comparison_forms(query)
    game_forms = comparison_forms(game.name)
    best = 0.0
    for query_form in query_forms:
        for game_form in game_forms:
            score = max(
                fuzz.token_set_ratio(query_form, game_form),
                fuzz.partial_ratio(query_form, game_form),
            )
            if query_form == game_form:
                score = max(score, 120)
            elif game_form.startswith(query_form):
                score = max(score, 105)
            query_tokens = set(query_form.split())
            game_tokens = set(game_form.split())
            score += len(query_tokens & game_tokens) * 2
            if _numbers(query_form) and _numbers(query_form) <= _numbers(game_form):
                score += 8
            best = max(best, float(score))
    return best


def search_games(
    query: str,
    games: list[Game],
    *,
    installed: bool | None = None,
    limit: int = 10,
    min_score: float = 35,
) -> list[Match]:
    candidates = games
    if installed is not None:
        candidates = [game for game in games if game.installed is installed]
    matches = [
        Match(game=game, score=score_game(query, game))
        for game in candidates
    ]
    matches = [match for match in matches if match.score >= min_score]
    matches.sort(key=lambda match: (-match.score, match.game.name.casefold()))
    return matches[:limit]


def is_clear_match(matches: list[Match]) -> bool:
    if not matches:
        return False
    if matches[0].score >= 115:
        return True
    if len(matches) == 1:
        return matches[0].score >= 85
    return matches[0].score >= 90 and matches[0].score - matches[1].score >= 15

