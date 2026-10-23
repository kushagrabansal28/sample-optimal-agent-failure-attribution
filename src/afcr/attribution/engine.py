"""The attribution engine: replay loop + confidence bookkeeping + stopping + rollout accounting.

Outcome statuses
----------------
identified        the stopping rule fired.  If ``guarantee_applies`` the answer is wrong with probability ≤ δ (Theorem 1)
                  *under the replay-model assumptions A1–A6* (paper §5.5).
budget_exhausted  the rollout budget ran out first — an ABSTENTION.  ``provisional`` is the empirical best guess and
                  ``candidate_set`` the arms not yet eliminated; a timeout is NOT a δ-PAC stopping event.
fixed_budget_done a fixed-budget strategy (equal_budget / random_budget / car_fixed_k) spent its quota; no guarantee.
oracle            reference answer from exact means (synthetic evaluation only).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..replay.base import ReplayEnv
from ..statistics.confidence import ConfidenceSequence, WilsonFixed
from .algorithms import Strategy, View
from .targets import Target

SHARE_MODES = ("none", "valid", "naive")


@dataclass
class AttributionResult:
    status: str
    selected: int | None
    provisional: int | None
    candidate_set: list[int]
    certified_none: bool
    guarantee_applies: bool
    guarantee_note: str
    delta: float
    total_rollouts: int
    total_steps: int
    own_pulls: list[int]
    shared_obs: list[int]
    successes: list[int]
    counts: list[int]
    means: list[float]
    lo: list[float]
    hi: list[float]
    eligible: list[bool]
    rounds: int
    wall_seconds: float
    strategy: str
    target: dict
    confidence: str
    share_mode: str
    reason: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def answer(self) -> int | None:
        """Forced-choice answer: certified selection if any, else the provisional best guess."""
        return self.selected if self.selected is not None else self.provisional

    @property
    def identified(self) -> bool:
        return self.status == "identified"

    def to_json(self) -> dict[str, Any]:
        d = {k: v for k, v in self.__dict__.items()}
        d["answer"] = self.answer
        return d


def run_attribution(env: ReplayEnv, strategy: Strategy, target: Target, conf: ConfidenceSequence, *, delta: float,
                    budget: int, rng: np.random.Generator, share: str = "none", history: bool = False,
                    history_stride: int = 1, meta: dict[str, Any] | None = None) -> AttributionResult:
    if not 0.0 < delta < 1.0:
        raise ValueError(f"delta must lie in (0, 1), got {delta!r}")
    if budget < 0 or int(budget) != budget:
        raise ValueError("budget must be a non-negative integer")
    if share not in SHARE_MODES:
        raise ValueError(f"share must be one of {SHARE_MODES}")
    if share == "valid" and not conf.valid_under_sharing:
        raise ValueError(f"confidence sequence {conf.name!r} is not proven valid under prefix sharing; "
                         "use 'stack_kl' (guaranteed) or share='naive' only as a negative control")
    if strategy.needs_wilson:
        conf = WilsonFixed(0.95)
    t0 = time.perf_counter()
    K_all = env.n_arms
    active = np.asarray(env.eligible, dtype=bool).copy()
    Ka = int(active.sum())
    if Ka == 0:
        raise ValueError("no eligible candidate arms")
    sharing_note = ""
    if share == "valid" and not env.sharing_valid:
        sharing_note = "environment does not satisfy the sharing conditions (e.g. state-reconstruction noise): sharing disabled"
        share = "none"

    s = np.zeros(K_all); n = np.zeros(K_all); own = np.zeros(K_all, dtype=int); shr = np.zeros(K_all, dtype=int)
    lo = np.zeros(K_all); hi = np.ones(K_all)
    mean = np.zeros(K_all)
    pulls = 0; steps = 0; rounds = 0
    hist: list[dict[str, Any]] = []
    anytime = conf.anytime_valid

    def refresh(dirty: list[int] | None) -> None:
        nonlocal lo, hi
        if conf.uses_rounds or dirty is None:
            ids = np.flatnonzero(active)
        else:
            ids = np.array([d for d in dirty if active[d]], dtype=int)
        if len(ids) == 0:
            return
        l, h = conf.bounds(s[ids], n[ids], K=Ka, delta=delta, rounds=max(rounds, 1))
        if anytime:                                   # running intersection: still valid on the good event, monotone
            l = np.maximum(l, lo[ids]); h = np.minimum(h, hi[ids])
            bad = l > h                               # only possible if the good event failed; keep the interval non-empty
            if bad.any():
                m = 0.5 * (l + h)
                l = np.where(bad, m, l); h = np.where(bad, m, h)
        lo[ids], hi[ids] = l, h
        mean[ids] = np.where(n[ids] > 0, s[ids] / np.maximum(n[ids], 1), 0.0)

    def view() -> View:
        return View(Ka, active, n, s, mean, lo, hi, rounds, pulls, rng, target)

    def finish(status: str, selected, provisional, cand, none_cert: bool, reason: str) -> AttributionResult:
        guarantee = (status == "identified" and conf.anytime_valid and not strategy.fixed_budget and share != "naive")
        note = ("δ-correct under assumptions A1–A6 (paper Thm 1" + (", Thm 3 for sharing" if share == "valid" else "") + ")") if guarantee \
            else ("no guarantee: " + ("fixed-budget strategy" if strategy.fixed_budget else
                  "naive sharing is statistically invalid" if share == "naive" else
                  "confidence sequence is not anytime-valid" if not conf.anytime_valid else "run did not stop on the rule"))
        if sharing_note:
            note += f" [{sharing_note}]"
        return AttributionResult(
            status=status, selected=selected, provisional=provisional, candidate_set=cand, certified_none=none_cert,
            guarantee_applies=bool(guarantee), guarantee_note=note, delta=delta, total_rollouts=pulls, total_steps=steps,
            own_pulls=own.astype(int).tolist(), shared_obs=shr.astype(int).tolist(), successes=s.astype(int).tolist(),
            counts=n.astype(int).tolist(), means=mean.tolist(), lo=lo.tolist(), hi=hi.tolist(),
            eligible=active.tolist(), rounds=rounds, wall_seconds=time.perf_counter() - t0, strategy=strategy.name,
            target=target.describe(), confidence=conf.name, share_mode=share, reason=reason, history=hist, meta=meta or {})

    if strategy.is_oracle:
        mu = env.true_means()
        if mu is None:
            raise ValueError("oracle strategy needs an environment that exposes true_means()")
        idx = np.flatnonzero(active)
        best = int(idx[np.argmax(mu[idx])])
        return finish("oracle", best, best, [best], False, "exact means")

    refresh(None)
    cap = budget
    q = strategy.quota(view())
    if q is not None:
        cap = min(cap, q) if budget else q

    while True:
        if not strategy.fixed_budget:
            dec = target.decide(lo, hi, mean, active)
            if dec is not None:
                return finish("identified", dec.selected, dec.selected, dec.certified_set, dec.selected is None, dec.reason)
        if pulls >= cap:
            break
        rounds += 1
        arms = strategy.select(view())
        if not arms:
            break
        dirty: set[int] = set()
        hnote = {"round": rounds, "pulls_before": pulls, "arms": [], "outcomes": [], "shared": {}}
        for a in arms:
            if pulls >= cap:
                break
            res = env.pull(a, rng)
            pulls += 1; steps += res.cost
            s[a] += res.outcome; n[a] += 1; own[a] += 1; dirty.add(a)
            hnote["arms"].append(int(a)); hnote["outcomes"].append(int(res.outcome))
            extra = res.shared_arms if share == "valid" else res.naive_shared_arms if share == "naive" else ()
            for j in extra:
                if active[j] and j != a:
                    s[j] += res.outcome; n[j] += 1; shr[j] += 1; dirty.add(j)
                    hnote["shared"][int(j)] = hnote["shared"].get(int(j), 0) + 1
        refresh(sorted(dirty))
        if history and (rounds % max(history_stride, 1) == 0):
            hnote["mean"] = [round(float(x), 5) for x in mean]
            hnote["lo"] = [round(float(x), 5) for x in lo]
            hnote["hi"] = [round(float(x), 5) for x in hi]
            hnote["counts"] = n.astype(int).tolist()
            sg = target.suggest(lo, hi, mean, n, active) if not strategy.fixed_budget else []
            hnote["suggested"] = [int(x) for x in sg]
            dec = None if strategy.fixed_budget else target.decide(lo, hi, mean, active)
            hnote["stop"] = dec is not None
            hist.append(hnote)

    # ended without a certified decision
    if strategy.fixed_budget:
        pick, cand = strategy.final(view())
        return finish("fixed_budget_done", None, pick, cand, False, "quota/budget spent; answer is the strategy's final rule")
    pick, cand = target.provisional(lo, hi, mean, active)
    return finish("budget_exhausted", None, pick, cand, False, "rollout budget exhausted before the stopping rule fired (abstention)")
