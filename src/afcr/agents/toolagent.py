"""Stage B: a controlled tool-using agent with planted failure types and EXACT ground truth.

Task ("order total"): compute  total = price * qty + shipping  by calling simulated tools, keeping results in memory,
validating, and recovering.  The agent is an explicit stochastic *program* over hashable snapshots, so a replay can
restore any prefix exactly (assumption A1), and exact intervention values come from memoised backward induction.

Planted failure types (each a fault action of the policy):
  planning      plan_bad       -> later lookups hit a decoy record (downstream propagation)
  tool choice   wrong_tool     -> the call returns garbage (-1)
  interpretation misread       -> a value is stored wrongly
  memory        mem_corrupt    -> the stored quantity is corrupted
  premature stop stop_early    -> shipping is skipped
  recovery      bad_recover    -> recovery step fails and the wrong answer is submitted

Variants:  stochastic (default)  |  deterministic (``deterministic=True``: one scheduled fault, noise 0, no recovery)
"""
from __future__ import annotations

import ast
import operator
from dataclasses import dataclass, replace
from functools import lru_cache

import numpy as np

PHASES = ["PLAN", "LOOKUP_PRICE", "LOOKUP_QTY", "LOOKUP_SHIP", "WRITE_MEMORY", "REASON", "VALIDATE", "RECOVER", "ANSWER"]


@dataclass(frozen=True)
class TState:
    phase: int = 0
    price: int | None = None
    qty: int | None = None
    ship: int | None = None
    total: int | None = None
    plan_ok: bool = True
    recov: int = 0
    retries: int = 0
    fb: int = 0                      # remaining scheduled faults (deterministic variant)
    done: bool = False
    answer: int | None = None


_OPS = {ast.Add: operator.add, ast.Mult: operator.mul, ast.Sub: operator.sub}


def safe_calc(expr: str) -> int:
    """The `calc` tool: evaluates + - * over integers only (no names, calls or attributes)."""
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            return n.value
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            return -ev(n.operand) if isinstance(n.op, ast.USub) else ev(n.operand)
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        raise ValueError(f"disallowed expression: {expr!r}")
    return int(ev(ast.parse(expr, mode="eval")))


class ToolAgentWorld:
    def __init__(self, price: int = 12, qty: int = 4, ship: int = 7, *, eps_plan: float = 0.15, eps_tool: float = 0.08,
                 eps_interp: float = 0.08, eps_mem: float = 0.12, eps_stop: float = 0.10, eps_rec: float = 0.25,
                 tool_noise: float = 0.10, catch_p: float = 0.75, false_alarm: float = 0.05, max_recov: int = 1,
                 horizon: int = 40, deterministic: bool = False, fault_phase: int = 4, name: str = "toolagent"):
        self.price, self.qty, self.ship = price, qty, ship
        self.gold = safe_calc(f"{price}*{qty}+{ship}")
        self.eps = dict(plan=eps_plan, tool=eps_tool, interp=eps_interp, mem=eps_mem, stop=eps_stop, rec=eps_rec)
        self.tool_noise, self.catch_p, self.false_alarm = tool_noise, catch_p, false_alarm
        self.max_recov, self.horizon, self.deterministic, self.fault_phase = max_recov, horizon, deterministic, fault_phase
        if deterministic:
            self.tool_noise, self.catch_p, self.false_alarm, self.max_recov = 0.0, 1.0, 0.0, 0
            self.eps = {k: 0.0 for k in self.eps}          # the only fault is the scheduled one (state field fb)
        self.name = name
        self._memo: dict = {}
        for k, v in self.eps.items():
            if not 0 <= v < 1:
                raise ValueError(f"eps_{k} must lie in [0,1)")
        self.fault_actions = {"plan_bad", "wrong_tool", "misread", "mem_corrupt", "stop_early", "bad_recover"}

    # ---- the simulated tools ------------------------------------------------------------------
    def tool_lookup(self, key: str, decoy: bool) -> int:
        true = {"price": self.price, "qty": self.qty, "ship": self.ship}[key]
        return true + 5 if decoy else true              # decoy record: a plausible but wrong entry

    @staticmethod
    def tool_calc(expr: str) -> int:
        return safe_calc(expr)

    def initial(self) -> TState:
        return TState(fb=1 if self.deterministic else 0)

    def is_terminal(self, s: TState) -> bool:
        return s.done

    def success(self, s: TState) -> bool:
        return s.done and s.answer == self.gold

    # ---- stochastic kernel: action -> (policy prob, [(prob, next_state)]) --------------------------------
    def actions(self, s: TState) -> dict[str, tuple[float, list[tuple[float, TState]]]]:
        """Actions the policy can choose (policy probability > 0)."""
        return {a: v for a, v in self._all_actions(s).items() if v[0] > 0}

    def _all_actions(self, s: TState) -> dict[str, tuple[float, list[tuple[float, TState]]]]:
        """Every defined action with its policy probability (possibly 0) and kernel - a forced reference action may have prob 0."""
        e, ph = self.eps, s.phase
        det_fault = self.deterministic and s.fb > 0 and ph == self.fault_phase
        out: dict[str, tuple[float, list[tuple[float, TState]]]] = {}

        def pol(good_name, fault_name, eps):
            if det_fault:
                return {good_name: 0.0, fault_name: 1.0}
            return {good_name: 1 - eps, fault_name: eps}

        if ph == 0:
            p = pol("plan_good", "plan_bad", e["plan"])
            out["plan_good"] = (p["plan_good"], [(1.0, replace(s, phase=1, plan_ok=True))])
            out["plan_bad"] = (p["plan_bad"], [(1.0, replace(s, phase=1, plan_ok=False, fb=max(s.fb - 1, 0)))])
        elif ph in (1, 2, 3):
            key = ("price", "qty", "ship")[ph - 1]
            if det_fault:
                pw, pm, pk = 1.0, 0.0, 0.0
            else:
                pw, pm = e["tool"], e["interp"]; pk = 1 - pw - pm
            val = self.tool_lookup(key, decoy=not s.plan_ok)

            def stored(v, nxt_extra=None):
                kw = {key: v, "phase": ph + 1, "retries": 0}
                return replace(s, **kw)
            ok_next = [(1 - self.tool_noise, stored(val))]
            if self.tool_noise > 0:
                if s.retries >= 3:
                    ok_next.append((self.tool_noise, replace(s, done=True, answer=None)))      # gives up
                else:
                    ok_next.append((self.tool_noise, replace(s, retries=s.retries + 1)))       # transient tool error -> retry
            out["lookup_ok"] = (pk, ok_next)
            out["wrong_tool"] = (pw, [(1.0, replace(stored(-1), fb=max(s.fb - (1 if det_fault else 0), 0)))])
            out["misread"] = (pm, [(1.0, stored(self.tool_lookup(key, decoy=False) + 10))])
        elif ph == 4:
            p = pol("mem_ok", "mem_corrupt", e["mem"])
            out["mem_ok"] = (p["mem_ok"], [(1.0, replace(s, phase=5))])
            out["mem_corrupt"] = (p["mem_corrupt"], [(1.0, replace(s, phase=5, qty=(s.qty or 0) + 1, fb=max(s.fb - 1, 0)))])
        elif ph == 5:
            p = pol("reason_ok", "stop_early", e["stop"])
            good = safe_calc(f"{s.price}*{s.qty}+{s.ship}")
            early = safe_calc(f"{s.price}*{s.qty}")
            out["reason_ok"] = (p["reason_ok"], [(1.0, replace(s, phase=6, total=good))])
            out["stop_early"] = (p["stop_early"], [(1.0, replace(s, phase=6, total=early, fb=max(s.fb - 1, 0)))])
        elif ph == 6:
            ans = replace(s, phase=8)
            rec = replace(s, phase=7)
            if s.total == self.gold:
                k = [(1 - self.false_alarm, ans)] + ([(self.false_alarm, rec)] if self.false_alarm > 0 else [])
            else:
                if s.recov >= self.max_recov:
                    k = [(1.0, ans)]
                else:
                    k = [(1 - self.catch_p, ans)] + ([(self.catch_p, rec)] if self.catch_p > 0 else [])
            out["validate"] = (1.0, k)
        elif ph == 7:
            if s.recov >= self.max_recov:
                out["replan"] = (1.0, [(1.0, replace(s, phase=8))])
            else:
                reset = TState(phase=1, plan_ok=True, recov=s.recov + 1, fb=s.fb)
                p = pol("replan", "bad_recover", e["rec"])
                out["replan"] = (p["replan"], [(1.0, reset)])
                out["bad_recover"] = (p["bad_recover"], [(1.0, replace(s, phase=8))])
        else:                                                  # ph == 8
            out["answer"] = (1.0, [(1.0, replace(s, done=True, answer=s.total))])
        return out

    def ref_action(self, s: TState) -> str:
        return {0: "plan_good", 1: "lookup_ok", 2: "lookup_ok", 3: "lookup_ok", 4: "mem_ok", 5: "reason_ok",
                6: "validate", 7: "replan", 8: "answer"}[s.phase]

    def ref_available(self, s: TState) -> bool:
        """The reference action must be an executable action; when the policy assigns it probability 0 (deterministic fault
        forced) we still allow forcing it (that IS the intervention)."""
        return True

    def _kernel(self, s: TState, a: str):
        """Kernel of action ``a`` at ``s`` even when the policy gives it probability 0 (a forced reference action)."""
        return self._all_actions(s)[a][1]

    # ---- simulation -----------------------------------------------------------------------------------
    def simulate(self, rng, s: TState, t: int, forced: str | None = None, record: bool = True):
        path = []
        first = True
        while t < self.horizon and not s.done:
            acts = self.actions(s)
            if first and forced is not None:
                a = forced
                kern = self._kernel(s, a)
            else:
                names = list(acts); probs = np.array([acts[n][0] for n in names])
                a = names[int(rng.choice(len(names), p=probs / probs.sum()))]
                kern = acts[a][1]
            first = False
            if record:
                path.append((t, s, a))
            ps = np.array([p for p, _ in kern])
            s = kern[int(rng.choice(len(kern), p=ps / ps.sum()))][1]
            t += 1
        return path, s, (t >= self.horizon and not s.done)

    def sample_original(self, rng):
        s, t = self.initial(), 0
        states, actions, faults = [s], [], []
        while t < self.horizon and not s.done:
            acts = self.actions(s)
            names = list(acts); probs = np.array([acts[n][0] for n in names])
            a = names[int(rng.choice(len(names), p=probs / probs.sum()))]
            if a in self.fault_actions:
                faults.append((t + 1, a))
            kern = acts[a][1]
            ps = np.array([p for p, _ in kern])
            s = kern[int(rng.choice(len(kern), p=ps / ps.sum()))][1]
            states.append(s); actions.append(a); t += 1
        return ToolTrajectory(states, actions, self.success(s), faults)

    def sample_failed(self, rng, *, require_fault=True, max_tries=100000):
        for _ in range(max_tries):
            tr = self.sample_original(rng)
            if not tr.success and tr.T >= 3 and (tr.faults or not require_fault):
                return tr
        raise RuntimeError("could not sample a failed trajectory (parameters too benign?)")

    # ---- exact values -------------------------------------------------------------------------------------
    def value(self, s: TState, t: int) -> float:
        if s.done:
            return 1.0 if s.answer == self.gold else 0.0
        if t >= self.horizon:
            return 0.0
        key = (s, t)
        if key in self._memo:
            return self._memo[key]
        v = 0.0
        for a, (pa, kern) in self.actions(s).items():
            v += pa * sum(p * self.value(n, t + 1) for p, n in kern)
        self._memo[key] = v
        return v

    def exact_mu(self, traj: "ToolTrajectory", intervention="repair", steps=None) -> np.ndarray:
        steps = list(range(1, traj.T + 1)) if steps is None else steps
        out = np.zeros(len(steps))
        for k, t in enumerate(steps):
            s = traj.states[t - 1]
            if intervention == "resample":
                out[k] = self.value(s, t - 1)
            else:
                kern = self._kernel(s, self.ref_action(s))
                out[k] = sum(p * self.value(n, t) for p, n in kern)
        return out

    def success_probability(self) -> float:
        return self.value(self.initial(), 0)

    # ---- narration (tool calls) -------------------------------------------------------------------------------
    def narrate(self, s: TState, a: str) -> str:
        ph = PHASES[s.phase]
        if ph == "PLAN":
            return "plan: " + ("order lookups correctly" if a == "plan_good" else "choose a decoy record (wrong plan)")
        if ph.startswith("LOOKUP"):
            key = ("price", "qty", "ship")[s.phase - 1]
            return {"lookup_ok": f"tool lookup({key}) -> {self.tool_lookup(key, not s.plan_ok)}", "wrong_tool": "calls `search` instead of lookup -> garbage",
                    "misread": f"lookup({key}) ok but value misread"}[a]
        return {"mem_ok": "write memory", "mem_corrupt": "memory write corrupts quantity", "reason_ok": f"calc({s.price}*{s.qty}+{s.ship})",
                "stop_early": "stops early: skips shipping", "validate": "validate total", "replan": "replan from lookups",
                "bad_recover": "recovery fails", "answer": "submit answer"}.get(a, a)


@dataclass
class ToolTrajectory:
    states: list[TState]
    actions: list[str]
    success: bool
    faults: list[tuple[int, str]]

    @property
    def T(self) -> int:
        return len(self.actions)

    @property
    def planted_cause(self) -> int | None:
        return self.faults[-1][0] if self.faults else None


def make_tool_world(seed: int = 0, **kw) -> ToolAgentWorld:
    rng = np.random.default_rng(seed)
    return ToolAgentWorld(price=int(rng.integers(5, 40)), qty=int(rng.integers(2, 9)), ship=int(rng.integers(3, 15)), **kw)
