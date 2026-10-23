"""HotpotQA agentic-QA adapter (Stage D) — loads a LOCAL HotpotQA-format JSON file you provide (distractor setting).

No HotpotQA data is downloaded or bundled and no HotpotQA result exists in this repository.  Dataset licence (CC BY-SA 4.0) was
read from secondary sources only.  Agent interface (documented, fixed):  actions are strings
    ``search: <query>``   -> returns the best-overlapping paragraph titles/snippets from the question's context
    ``finish: <answer>``  -> ends the episode; success iff normalised exact match with the gold answer
Evaluation: normalised EM (lower-casing, punctuation/article removal) — same evaluator for every method.
Fixture for tests: ``toy_fixture()`` — two hand-written questions in HotpotQA format (NOT HotpotQA data).
"""
from __future__ import annotations

import json
import re
import string

from .textgame import BenchmarkUnavailable


def normalize(s: str) -> str:
    s = s.lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def exact_match(pred: str, gold: str) -> bool:
    return normalize(pred) == normalize(gold)


class HotpotQAGame:
    def __init__(self, items: list[dict], max_steps: int = 8):
        if not items:
            raise ValueError("no questions")
        self.items, self.max_steps = items, max_steps
        self._i = 0; self._n = 0; self._done = False

    @classmethod
    def from_file(cls, path: str, **kw):
        try:
            with open(path, encoding="utf-8") as fh:
                return cls(json.load(fh), **kw)
        except FileNotFoundError as e:
            raise BenchmarkUnavailable(f"HotpotQA file not found: {path} (download hotpot_dev_distractor_v1.json yourself)") from e

    def reset(self, seed: int) -> str:
        self._i, self._n, self._done = seed % len(self.items), 0, False
        return "Question: " + self.items[self._i]["question"]

    def _search(self, q: str) -> str:
        toks = set(normalize(q).split())
        scored = []
        for title, sents in self.items[self._i]["context"]:
            text = " ".join(sents)
            scored.append((len(toks & set(normalize(title + " " + text).split())), title, text))
        scored.sort(reverse=True)
        return " || ".join(f"{t}: {x[:160]}" for _, t, x in scored[:2])

    def step(self, action: str):
        self._n += 1
        if self._done:
            return "episode finished", True, False
        a = action.strip()
        if a.lower().startswith("finish:"):
            self._done = True
            return "finished", True, exact_match(a.split(":", 1)[1], self.items[self._i]["answer"])
        if a.lower().startswith("search:"):
            obs = self._search(a.split(":", 1)[1])
        else:
            obs = "invalid action; use `search: <query>` or `finish: <answer>`"
        if self._n >= self.max_steps:
            self._done = True
            return obs, True, False
        return obs, False, False

    def admissible(self) -> list[str]:
        return []


def toy_fixture() -> list[dict]:
    return [
        {"question": "Which city is the capital of the country where the Eiffel Tower stands?", "answer": "Paris",
         "context": [["Eiffel Tower", ["The Eiffel Tower is in France."]], ["France", ["The capital of France is Paris."]],
                     ["Berlin", ["Berlin is the capital of Germany."]]]},
        {"question": "Who wrote the novel adapted into the film Blade Runner?", "answer": "Philip K. Dick",
         "context": [["Blade Runner", ["Blade Runner is based on a novel by Philip K. Dick."]], ["Dune", ["Dune was written by Frank Herbert."]]]},
    ]
