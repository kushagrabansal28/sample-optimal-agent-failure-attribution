"""FastAPI backend.  Run:  uvicorn afcr.api.app:app --port 8000   (serves the built website from website/dist at /)."""
from __future__ import annotations

import csv
import io
import json
import logging
from functools import lru_cache
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from ..agents.toolagent import ToolAgentWorld, make_tool_world
from ..attribution import ArgmaxEps, FirstAbove, LastAbove, make_strategy, run_attribution
from ..automata.base import EPS, AutomatonError
from ..automata.benchmark48 import build_agent_model
from ..automata.dfa import SINK
from . import lab
from ..replay import AutomatonEnv, ToolAgentEnv, make_automaton_instance, make_gap_instance, make_toolagent_instance
from ..statistics import make_confidence

ROOT = Path(__file__).resolve().parents[3]
PROC = ROOT / "results" / "processed"
log = logging.getLogger("afcr.api")
app = FastAPI(title="AFCR API", version="0.2.0", docs_url="/api/docs", redoc_url="/api/redoc",
              description="Automata-Aware Fixed-Confidence Replay: automata, replay, attribution, experiments. All results are SYNTHETIC unless stated.")


@app.exception_handler(ValidationError)
async def _validation_error(_: Request, exc: ValidationError):
    """A pydantic error raised inside a handler (e.g. while building an inner request model) is the caller's fault: 422, not 500."""
    errs = [{"loc": ["body", *map(str, e.get("loc", ()))], "msg": e.get("msg", ""), "type": e.get("type", "")} for e in exc.errors()]
    return JSONResponse({"detail": errs}, status_code=422)


@lru_cache(maxsize=16)
def agent(n_states: int = 48, eps_plan: float = 0.6):
    try:
        return build_agent_model(n_states, eps={"PLAN_SUBGOAL": eps_plan})
    except AutomatonError as e:
        raise HTTPException(422, str(e))


# =============================================================================================== automata
class TraceReq(BaseModel):
    model: str
    word: list[str] = Field(default_factory=list, max_length=200)
    n_states: int = Field(48, ge=48, le=96)
    seed: int = Field(0, ge=0)
    view: str = "lts"


@app.get("/api/health")
def health():
    return {"status": "ok", "version": app.version}


@app.get("/api/automata/models")
def list_models():
    return [{"id": k, **v} for k, v in lab.MODEL_INFO.items()]


def _agent_view(m, view: str, eps_plan: float):
    d = m.describe()
    edges = []
    sink = None
    if view == "dfa":
        dfa = m.to_dfa()
        explicit: dict[str, int] = {}
        for (q, a), r in dfa.delta.items():
            if q in m.specs and r in m.specs:
                edges.append({"source": q, "target": r, "label": a, "is_fault": a in m.fault_symbols(), "prob": None})
                explicit[q] = explicit.get(q, 0) + 1
        # the DFA is total: every other symbol leads to the explicit, non-logical sink (drawn aggregated, one edge per state)
        sink = {"id": SINK, "label": "sink (not a logical state)", "sink": True, "kind": "nonterminal", "role": "sink",
                "description": "Completion artefact: every symbol that is not enabled in a state leads here. It is not counted as a logical state."}
        for q in m.specs:
            others = len(dfa.alphabet) - explicit.get(q, 0)
            if others:
                edges.append({"source": q, "target": SINK, "label": f"{others} other symbols", "is_fault": False, "prob": None})
    elif view in ("nfa", "enfa"):
        auto = m.to_nfa() if view == "nfa" else m.to_enfa()
        for (q, a), rs in auto.delta.items():
            for r in rs:
                edges.append({"source": q, "target": r, "label": a, "is_fault": a in m.fault_symbols(), "epsilon": a == EPS, "prob": None})
    elif view == "pa":
        for s, sp in m.specs.items():
            for a, spec in sp.actions.items():
                for r, p in spec.next.items():
                    edges.append({"source": s, "target": r, "label": a, "is_fault": spec.is_fault, "prob": p})
    else:
        edges = d["edges"]
    for i, n in enumerate(d["nodes"]):                    # q0 ... q47 in definition order (PLAN, OBSERVE, TOOL, MEMORY, VALIDATE, TERMINAL)
        n["qid"] = f"q{i}"
        n["name"] = n["id"]
    if sink:
        sink["qid"] = f"q{len(d['nodes'])}"
        sink["name"] = SINK
        d["nodes"] = [*d["nodes"], sink]
    d["edges"], d["view"] = edges, view
    return d


@app.get("/api/automata/graph")
def graph(model: str, n_states: int = Query(48, ge=48, le=96), view: str | None = None, eps_plan: float = Query(0.6, ge=0.0, lt=1.0)):
    if model == "agent48":
        view = view or "lts"
        if view not in ("lts", "dfa", "nfa", "enfa", "pa"):
            raise HTTPException(422, "view must be lts|dfa|nfa|enfa|pa")
        m = agent(n_states, eps_plan)
        d = _agent_view(m, view, eps_plan)
        d["count_logical_states"] = m.count_logical_states()
        try:
            m.validate()
            d["state_count_validated"] = True
        except AutomatonError:
            d["state_count_validated"] = False
        d["info"] = lab.MODEL_INFO["agent48"]
        d["kind"] = "agent"
        return d
    if model not in lab.MODEL_INFO:
        raise HTTPException(404, f"unknown model {model}")
    try:
        return lab.graph_payload(model, view)
    except AutomatonError as e:
        raise HTTPException(422, str(e))


@app.post("/api/automata/trace")
def trace(req: TraceReq):
    try:
        if req.model == "agent48":
            m = agent(req.n_states)
            if req.word:                                    # run a user-given action word through the DFA skeleton
                d = m.to_dfa()
                t = d.run(req.word)
                return {"model": "agent48-dfa", "kind": "agent", "accepted": t.accepted, "steps": [s.to_json() for s in t.steps]}
            tr = m.sample_original(np.random.default_rng(req.seed))
            return {"model": "agent48", "kind": "agent", "success": tr.success, "faults": tr.fault_symbols, "fault_steps": tr.fault_steps,
                    "steps": [{"index": i, "state": m.ids[tr.states[i]], "symbol": m.sym_ids[tr.states[i]][tr.actions[i]], "next_state": m.ids[tr.states[i + 1]],
                               "is_fault": bool(m.fault_mask[tr.states[i]][tr.actions[i]])} for i in range(tr.T)]}
        if req.model not in lab.MODEL_INFO:
            raise HTTPException(404, "unknown model")
        return lab.trace_payload(req.model, req.word, req.seed)
    except AutomatonError as e:
        raise HTTPException(422, str(e))


@app.get("/api/automata/compare")
def compare():
    return lab.compare_rows()


# =============================================================================================== attribution
class AttribReq(BaseModel):
    source: str = Field("automaton", pattern="^(automaton|bandit|toolagent)$")
    seed: int = Field(0, ge=0)
    n_states: int = Field(48, ge=48, le=200)
    eps_plan: float = Field(0.6, ge=0.0, lt=1.0)
    gap: float = Field(0.2, gt=0.0, lt=0.7)
    K: int = Field(8, ge=2, le=60)
    algorithm: str = "lucb"
    target: str = "argmax"
    eps: float = Field(0.0, ge=0.0, le=0.5)
    theta: float = Field(0.5, ge=0.0, le=1.0)
    delta: float = Field(0.1, gt=0.0, lt=1.0)
    budget: int = Field(20000, ge=1, le=300000)
    share: str = Field("none", pattern="^(none|valid|naive)$")
    confidence: str = "stack_kl"
    intervention: str = Field("repair", pattern="^(repair|resample)$")
    candidates: str = Field("all", pattern="^(all|decision)$")
    reconstruct_noise: float = Field(0.0, ge=0.0, le=1.0)
    deterministic: bool = False
    history: bool = True


def build_env(r: AttribReq):
    if r.source == "bandit":
        return make_gap_instance(r.K, r.gap, best=0.8)
    if r.source == "toolagent":
        w = ToolAgentWorld(deterministic=True, fault_phase=4) if r.deterministic else make_tool_world(r.seed)
        return make_toolagent_instance(w, np.random.default_rng(r.seed), intervention=r.intervention)
    m = agent(r.n_states, r.eps_plan)
    return make_automaton_instance(m, np.random.default_rng(r.seed), intervention=r.intervention, candidates=r.candidates,
                                   state_reconstruction_noise=r.reconstruct_noise)


def _target(r: AttribReq):
    if r.target == "argmax":
        return ArgmaxEps(r.eps)
    if r.target == "first_above":
        return FirstAbove(r.theta)
    if r.target == "last_above":
        return LastAbove(r.theta)
    raise HTTPException(422, "target must be argmax | first_above | last_above")


@app.post("/api/attribute")
def attribute(r: AttribReq):
    try:
        env = build_env(r)
        res = run_attribution(env, make_strategy(r.algorithm), _target(r), make_confidence(r.confidence), delta=r.delta, budget=r.budget,
                              rng=np.random.default_rng(r.seed + 7), share=r.share, history=r.history,
                              history_stride=max(1, r.budget // 500), meta={"seed": r.seed, "source": r.source})
    except (ValueError, AutomatonError) as e:
        raise HTTPException(422, str(e))
    out = res.to_json()
    mu = env.true_means()
    out["ground_truth"] = {"true_means": mu.tolist(), "argmax_arm": int(np.argmax(mu)), "planted_arm": env.planted_arm(), "labels": env.arm_labels, "synthetic": True}
    if isinstance(env, AutomatonEnv):
        m = env.model
        out["trajectory"] = [{"t": t + 1, "state": m.ids[env.traj.states[t]], "action": m.sym_ids[env.traj.states[t]][env.traj.actions[t]],
                              "is_fault": bool(m.fault_mask[env.traj.states[t]][env.traj.actions[t]])} for t in range(env.traj.T)]
        out["steps"] = env.steps
    elif isinstance(env, ToolAgentEnv):
        w = env.world
        out["trajectory"] = [{"t": t + 1, "state": env.arm_labels[t].split(": ")[1], "action": env.traj.actions[t], "is_fault": env.traj.actions[t] in w.fault_actions,
                              "note": w.narrate(env.traj.states[t], env.traj.actions[t])} for t in range(env.traj.T)]
        out["steps"] = env.steps
    out["labels"] = env.arm_labels
    out["sharing_valid"] = bool(env.sharing_valid)
    return out


class ReplayReq(BaseModel):
    source: str = Field("automaton", pattern="^(automaton|toolagent)$")
    seed: int = Field(0, ge=0)
    arm: int = Field(0, ge=0)
    eps_plan: float = Field(0.6, ge=0.0, lt=1.0)
    intervention: str = Field("repair", pattern="^(repair|resample)$")
    n_states: int = Field(48, ge=48, le=96)
    deterministic: bool = False
    replay_seed: int | None = Field(None, ge=0)


@app.post("/api/replay")
def replay(r: ReplayReq):
    ar = AttribReq(source=r.source, seed=r.seed, eps_plan=r.eps_plan, n_states=r.n_states, intervention=r.intervention, deterministic=r.deterministic)
    env = build_env(ar)
    if not 0 <= r.arm < env.n_arms:
        raise HTTPException(422, f"arm must be in [0, {env.n_arms - 1}]")
    if isinstance(env, AutomatonEnv):
        m = env.model
        orig = [{"t": t + 1, "state": m.ids[env.traj.states[t]], "action": m.sym_ids[env.traj.states[t]][env.traj.actions[t]],
                 "is_fault": bool(m.fault_mask[env.traj.states[t]][env.traj.actions[t]])} for t in range(env.traj.T)]
    else:
        w = env.world
        orig = [{"t": t + 1, "state": env.arm_labels[t].split(": ")[1], "action": env.traj.actions[t], "is_fault": env.traj.actions[t] in w.fault_actions,
                 "note": w.narrate(env.traj.states[t], env.traj.actions[t])} for t in range(env.traj.T)]
    cf = env.replay_detail(r.arm, np.random.default_rng(r.seed + 99 if r.replay_seed is None else r.replay_seed))
    return {"original": orig, "counterfactual": cf, "exact_mu": float(env.true_means()[r.arm]), "original_outcome": "failure",
            "note": "A real intervention: the continuation is re-simulated under the same stochastic policy from the intervened state - not a relabelled trace."}


class TrajReq(BaseModel):
    source: str = Field("automaton", pattern="^(automaton|toolagent)$")
    seed: int = Field(0, ge=0)
    eps_plan: float = Field(0.6, ge=0.0, lt=1.0)
    n_states: int = Field(48, ge=48, le=96)
    intervention: str = Field("repair", pattern="^(repair|resample)$")
    deterministic: bool = False


def _traj_payload(env):
    if isinstance(env, AutomatonEnv):
        m = env.model
        steps = [{"t": t + 1, "state": m.ids[env.traj.states[t]], "action": m.sym_ids[env.traj.states[t]][env.traj.actions[t]],
                  "ref_action": m.sym_ids[env.traj.states[t]][int(m.ref_idx[env.traj.states[t]])],
                  "is_fault": bool(m.fault_mask[env.traj.states[t]][env.traj.actions[t]]), "group": m.specs[m.ids[env.traj.states[t]]].info.group,
                  "role": m.specs[m.ids[env.traj.states[t]]].info.role, "next_state": m.ids[env.traj.states[t + 1]]} for t in range(env.traj.T)]
        base = float(m.success_probability())
    else:
        w = env.world
        steps = [{"t": t + 1, "state": env.arm_labels[t].split(": ")[1], "action": env.traj.actions[t], "ref_action": w.ref_action(env.traj.states[t]),
                  "is_fault": env.traj.actions[t] in w.fault_actions, "note": w.narrate(env.traj.states[t], env.traj.actions[t]),
                  "memory": {"price": env.traj.states[t].price, "qty": env.traj.states[t].qty, "ship": env.traj.states[t].ship, "total": env.traj.states[t].total}}
                 for t in range(env.traj.T)]
        base = float(w.success_probability())
    mu = env.true_means()
    return {"steps": steps, "exact_mu": mu.tolist(), "baseline_success": base, "planted_arm": env.planted_arm(), "argmax_arm": int(np.argmax(mu)),
            "intervention": env.intervention, "labels": env.arm_labels, "outcome": "failure", "synthetic": True}


@app.post("/api/trajectory")
def trajectory(r: TrajReq):
    env = build_env(AttribReq(source=r.source, seed=r.seed, eps_plan=r.eps_plan, n_states=r.n_states, intervention=r.intervention, deterministic=r.deterministic))
    return _traj_payload(env)


class EstReq(ReplayReq):
    n: int = Field(200, ge=1, le=5000)


@app.post("/api/replay/estimate")
def replay_estimate(r: EstReq):
    from ..automata.pa import wilson_interval
    ar = AttribReq(source=r.source, seed=r.seed, eps_plan=r.eps_plan, n_states=r.n_states, intervention=r.intervention, deterministic=r.deterministic)
    env = build_env(ar)
    if not 0 <= r.arm < env.n_arms:
        raise HTTPException(422, f"arm must be in [0, {env.n_arms - 1}]")
    rng = np.random.default_rng(r.seed + 1234)
    k = sum(env.pull(r.arm, rng).outcome for _ in range(r.n))
    lo, hi = wilson_interval(k, r.n, 0.95)
    return {"arm": r.arm, "n": r.n, "successes": k, "mean": k / r.n, "ci_lo": lo, "ci_hi": hi, "level": 0.95, "exact_mu": float(env.true_means()[r.arm]),
            "note": "fixed-n Wilson interval for a single pre-specified sample size (not an anytime-valid bound)"}


@app.get("/api/tests")
def tests_report():
    p = PROC / "test_report.json"
    if not p.exists():
        return {"available": False}
    d = json.loads(p.read_text(encoding="utf-8"))
    fp = PROC / "frontend_test_report.json"
    if fp.exists():
        f = json.loads(fp.read_text(encoding="utf-8"))
        d["frontend"] = {"total": f.get("numTotalTests", 0), "passed": f.get("numPassedTests", 0), "failed": f.get("numFailedTests", 0), "command": "cd website && npm test"}
    return d


MAX_EXPERIMENT_ROLLOUTS = 2_000_000


class ExpReq(BaseModel):
    source: str = Field("bandit", pattern="^(bandit|automaton|toolagent)$")
    algorithms: list[str] = ["lucb", "uniform_fc", "successive_elim"]
    trials: int = Field(10, ge=1, le=60)
    K: int = Field(8, ge=2, le=40)
    gap: float = Field(0.2, gt=0.0, lt=0.7)
    delta: float = Field(0.1, gt=0.0, lt=1.0)
    budget: int = Field(20000, ge=100, le=100000)
    seed: int = Field(0, ge=0)
    eps_plan: float = Field(0.6, ge=0.0, lt=1.0)
    n_states: int = Field(48, ge=48, le=96)


@app.post("/api/experiment/run")
def run_experiment(r: ExpReq):
    from ..experiments.core import METHODS, run_spec
    from ..evaluation.metrics import summarize
    if r.trials * len(r.algorithms) * r.budget > MAX_EXPERIMENT_ROLLOUTS:
        raise HTTPException(422, f"requested work ({r.trials} trials x {len(r.algorithms)} algorithms x budget {r.budget}) exceeds the limit of "
                                 f"{MAX_EXPERIMENT_ROLLOUTS:,} rollouts per request; reduce trials, algorithms or budget (use the experiment suite for large runs)")
    bad = [a for a in r.algorithms if a not in METHODS]
    if bad:
        raise HTTPException(422, f"unknown algorithm(s): {bad}; choose from {sorted(METHODS)}")
    rows = []
    for alg in r.algorithms:
        for s in range(r.trials):
            sp = dict(kind=r.source, method=alg, seed=r.seed + s, K=r.K, gap=r.gap, delta=r.delta, budget=r.budget, eps_plan=r.eps_plan, n_states=r.n_states, tags={})
            try:
                row = run_spec(sp)
            except (ValueError, AutomatonError) as e:
                raise HTTPException(422, str(e))
            rows.append({k: row[k] for k in ("method", "seed", "answer", "truth", "correct", "correct_exact", "identified", "abstained", "rollouts", "shared", "gap", "n_arms")})
    summ = summarize(rows)
    clean = [{k: (list(v) if isinstance(v, tuple) else v) for k, v in s.items()} for s in summ]
    return {"rows": rows, "summary": clean, "synthetic": True, "config": r.model_dump()}


# =============================================================================================== results & research
def _load(name: str):
    p = PROC / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


@app.get("/api/results/index")
def results_index():
    groups = sorted(p.stem for p in PROC.glob("*.json") if p.stem not in ("suite_meta", "paired_stats", "test_report", "frontend_test_report"))
    return {"available": bool(groups), "groups": groups, "meta": _load("suite_meta.json"), "paired": _load("paired_stats.json"),
            "figures": _load("../figures/manifest.json") if (ROOT / "results" / "figures" / "manifest.json").exists() else None}


@app.get("/api/results/group/{name}")
def results_group(name: str):
    d = _load(f"{name}.json") if name.replace("_", "").isalnum() else None
    if d is None:
        raise HTTPException(404, f"no results for group {name!r}; run `python -m afcr.experiments.suite`")
    return d


@app.get("/api/results/summary")                    # backward compatible alias for the main group
def results_summary():
    d = _load("main.json")
    return {"available": d is not None, **(d or {}), "meta": _load("suite_meta.json")}


@app.get("/api/results/export")
def results_export(fmt: str = Query("json", pattern="^(json|csv)$"), group: str = "main"):
    if not group.replace("_", "").isalnum():
        raise HTTPException(422, "bad group")
    p = ROOT / "results" / "raw" / f"{group}.csv"
    if not p.exists():
        raise HTTPException(404, "no raw results for that group")
    if fmt == "csv":
        return PlainTextResponse(p.read_text(encoding="utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={group}.csv"})
    return {"rows": list(csv.DictReader(io.StringIO(p.read_text(encoding="utf-8"))))}


@app.get("/api/research/{what}")
def research(what: str):
    f = {"novelty": "novelty_matrix.csv", "related": "related_work.csv"}.get(what)
    if not f:
        raise HTTPException(404, "novelty | related")
    return list(csv.DictReader((ROOT / "research" / f).open(encoding="utf-8")))


@app.get("/api/status")
def status():
    p = ROOT / "RESEARCH_STATUS.md"
    return PlainTextResponse(p.read_text(encoding="utf-8") if p.exists() else "missing")


# =============================================================================================== static files
for sub in ("results", "paper", "report", "presentation", "research"):
    d = ROOT / sub
    if d.exists():
        app.mount(f"/files/{sub}", StaticFiles(directory=d), name=f"files-{sub}")
for fname in ("RESEARCH_STATUS.md", "DELIVERY_SUMMARY.md", "README.md"):
    def _mk(f=fname):
        @app.get(f"/files/{f}", summary=f"Download {f}")
        def _f():
            return FileResponse(ROOT / f, media_type="text/markdown")
    _mk()

DIST = ROOT / "website" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.split("/", 1)[0] in ("api", "files"):         # unknown API / file routes are errors, not the web page
            raise HTTPException(404, "Not Found")
        root = DIST.resolve()
        f = (DIST / full_path).resolve()
        if full_path and f.is_file() and f.is_relative_to(root):  # never serve anything outside website/dist
            return FileResponse(f)
        return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-cache"})

else:
    @app.get("/", include_in_schema=False)
    def no_build():
        return PlainTextResponse("Website not built. Run: cd website && npm install && npm run build  (API docs at /docs)")
