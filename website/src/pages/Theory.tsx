import { Sigma } from 'lucide-react'
import { Badge, Callout, Card, CodeBlock, Disclosure, PageHeader, Proved, Reveal, Tex } from '../ui/kit'

const PSEUDO = `AFCR(env, target, δ, budget):
  for each eligible step t:  N_t = 0, S_t = 0                      # one arm per candidate
  loop:
    [lo_t, hi_t] ← KL ball of radius x_n / n,  x_n = ln(2·K·n·(n+1)/δ)   (running intersection)
    if target.decide(lo, hi):   return certified answer             # δ-guarantee applies (Thm 1)
    if rollouts ≥ budget:       return ABSTAIN(candidate set)       # NOT a δ-PAC event
    arms ← unseen arms first;  else { h = argmax mean,  ℓ = argmax_{a≠h} hi_a }   # LUCB
    for a in arms:
        y ← replay(a)                  # a REAL intervention + re-simulation
        update (N_a, S_a) with y
        if prefix-aware:               # only exact (time,state,action) matches (Thm 3)
            for j in matched_arms(rollout): update (N_j, S_j) with y`

export default function Theory() {
  return (
    <div className="stack" style={{ gap: 22 }}>
      <PageHeader eyebrow="Guarantees" title="Theory and what is actually proved" lead="Statements are marked proved, cited or empirical. Proofs are complete for the claims labelled proved; nothing is presented as a theorem unless it is one." right={<Badge kind="info"><Sigma size={13} /> KaTeX</Badge>} />

      <Reveal><Card title="1 · The formal problem and the estimand">
        <p>A failed trajectory <Tex>{'\\tau=(q_0,a_1,q_1,\\dots,a_T,q_T)'}</Tex>, outcome <Tex>{'Y\\in\\{0,1\\}'}</Tex>. For each candidate step <Tex>{'t'}</Tex> and an intervention <Tex>{'g_t'}</Tex> (<b>repair</b>: force the reference action <Tex>{'\\rho(q_{t-1})'}</Tex>; <b>resample</b>: redraw from <Tex>{'\\pi'}</Tex>) the continuation runs under the same stochastic policy:</p>
        <Tex block>{'\\mu_t=\\Pr\\big(Y^{(t,g_t)}=1\\ \\big|\\ \\text{replay context}\\big),\\qquad \\Delta_t=\\mu_t-\\mu_{\\mathrm{ref}}'}</Tex>
        <p className="small muted">The reference <Tex>{'\\mu_{\\mathrm{ref}}'}</Tex> (success probability of the unintervened agent) is common to all steps, so ranking by <Tex>{'\\Delta_t'}</Tex> equals ranking by <Tex>{'\\mu_t'}</Tex>. Different interventions give different rankings: the protocol is part of the estimand.</p>
        <div className="grid cols-3">
          <Callout title="argmax-ε">Return <Tex>{'h'}</Tex> with <Tex>{'\\mu_h\\ge\\max_a\\mu_a-\\varepsilon'}</Tex>. With ε = 0 it certifies the <em>unique</em> best step; ties end in abstention.</Callout>
          <Callout title="first-above-θ">The <em>earliest</em> step with <Tex>{'\\mu_t\\ge\\theta'}</Tex> (AgenTracer’s decisive step). Exactly correct on the good event.</Callout>
          <Callout title="last-above-θ">The <em>latest</em> step still above θ (CAR’s point of commitment, with a margin). Exactly correct on the good event.</Callout>
        </div>
        <p className="small muted" style={{ marginBottom: 0 }}>Not equated: temporal association, predictive power, interventional effect, unique responsibility, joint necessary causes. This work identifies the <b>interventional effect of a repair</b>; joint causes are out of scope.</p>
      </Card></Reveal>

      <Reveal><Card title="2 · Statistical assumptions">
        <div className="tbl-wrap"><table className="tbl"><thead><tr><th>#</th><th className="wrap">Assumption</th><th className="wrap">Toy automata</th><th className="wrap">Controlled agent</th><th className="wrap">Production LLM agent</th></tr></thead><tbody>
          {[['A1', 'The replay starts from exactly the original state q_{t−1} at time t−1', 'holds', 'holds (snapshots)', 'often violated (hidden context, tools)'],
            ['A2', 'Markov on time-augmented states; outcome depends only on the terminal state', 'holds', 'holds', 'usually violated — mitigate with history as state'],
            ['A3', 'Intervention and continuation policy fixed across pulls and arms (stationary)', 'holds', 'holds', 'violated by model updates, provider drift'],
            ['A4', 'Fresh independent randomness per rollout', 'holds', 'holds', 'violated by cached / batched inference'],
            ['A5', 'The intervention changes only the designated step', 'holds', 'holds', 'hard to guarantee for natural-language edits'],
            ['A6', 'The target is the declared interventional estimand in the replay context', 'by definition', 'by definition', 'must be argued per use']].map((r) => <tr key={r[0]}><td className="mono"><b>{r[0]}</b></td><td className="wrap">{r[1]}</td><td className="wrap">{r[2]}</td><td className="wrap">{r[3]}</td><td className="wrap">{r[4]}</td></tr>)}</tbody></table></div>
        <p className="small muted" style={{ marginBottom: 0 }}>Adaptivity and repeated decisions are handled by the anytime-valid (all sample sizes, all arms) confidence sequence plus a union bound — no multiple-testing correction is applied afterwards because none is needed.</p>
      </Card></Reveal>

      <Reveal><Card title="3 · The algorithm and its stopping rule"><CodeBlock code={PSEUDO} lang="pseudocode" />
        <p className="small muted" style={{ marginBottom: 0 }}>The sampling rule can be anything: Theorem 1 does not depend on it. Budget exhaustion returns the empirical best guess <em>and</em> the arms not yet eliminated, flagged as an abstention.</p>
      </Card></Reveal>

      <Reveal><Card title="4 · Theorems and proofs" right={<Proved />}>
        <div className="stack">
          <Disclosure defaultOpen title={<>Theorem 1 — δ-correctness for any sampling rule <Proved /></>}>
            <p><b>Setting.</b> Arm <Tex>{'a\\in[K]'}</Tex> with unknown <Tex>{'\\mu_a'}</Tex>; per-arm i.i.d. Bernoulli observations <Tex>{'X_{a,1},X_{a,2},\\dots'}</Tex>. Let <Tex>{'\\mathrm{kl}'}</Tex> be the Bernoulli KL, <Tex>{'x_n=\\ln\\frac{2Kn(n+1)}{\\delta}'}</Tex> and <Tex>{'B_{a,n}=\\{q:\\,n\\,\\mathrm{kl}(\\hat\\mu_{a,n},q)\\le x_n\\}'}</Tex>.</p>
            <p><b>Claim.</b> <Tex>{'\\Pr(\\exists a,n:\\ \\mu_a\\notin B_{a,n})\\le\\delta'}</Tex>. Hence a rule that returns <Tex>{'h'}</Tex> when <Tex>{'\\mathrm{lo}_h+\\varepsilon\\ge\\max_{a\\ne h}\\mathrm{hi}_a'}</Tex> errs with probability <Tex>{'\\le\\delta'}</Tex>, whatever the sampling rule.</p>
            <p><b>Proof.</b> <em>Reward-stack model:</em> the <Tex>{'n'}</Tex>-th pull of arm <Tex>{'a'}</Tex> reveals <Tex>{'X_{a,n}'}</Tex> no matter when it happens, so for fixed <Tex>{'(a,n)'}</Tex> the first <Tex>{'n'}</Tex> entries are i.i.d. and adaptivity only chooses <em>which</em> <Tex>{'n'}</Tex> is observed. For fixed <Tex>{'(a,n)'}</Tex>, <Tex>{'\\mu_a<\\mathrm{lo}'}</Tex> means <Tex>{'\\hat\\mu>\\mu_a'}</Tex> and <Tex>{'n\\,\\mathrm{kl}(\\hat\\mu,\\mu_a)>x_n'}</Tex>, i.e. <Tex>{'\\hat\\mu\\ge u'}</Tex> with <Tex>{'n\\,\\mathrm{kl}(u,\\mu_a)=x_n'}</Tex>; by the Chernoff bound this has probability at most <Tex>{'e^{-x_n}'}</Tex>. The upper tail is symmetric, so <Tex>{'\\Pr(\\mu_a\\notin B_{a,n})\\le 2e^{-x_n}=\\delta/(Kn(n+1))'}</Tex>. Summing over <Tex>{'a\\le K'}</Tex> and <Tex>{'n\\ge1'}</Tex> and using <Tex>{'\\sum_n\\frac1{n(n+1)}=1'}</Tex> gives <Tex>{'\\le\\delta'}</Tex>. On the complement event every interval contains its mean; if the rule stops with <Tex>{'\\mathrm{lo}_h+\\varepsilon\\ge\\mathrm{hi}_a\\ge\\mu_a'}</Tex> for all <Tex>{'a\\ne h'}</Tex>, then <Tex>{'\\mu_h\\ge\\mathrm{lo}_h\\ge\\mu_a-\\varepsilon'}</Tex>. A running intersection of intervals preserves coverage on this event. Dependence between arms is irrelevant (union bound). ∎</p>
          </Disclosure>
          <Disclosure title={<>Theorem 2 — sample complexity of successive elimination <Badge kind="ok">proved (SE only)</Badge></>}>
            <p>With gaps <Tex>{'\\Delta_a>0'}</Tex> and half-width <Tex>{'w_n\\le\\sqrt{x_n/(2n)}'}</Tex> (Pinsker), on the good event a suboptimal arm is eliminated once <Tex>{'\\Delta_a>4w_n'}</Tex>, which holds for <Tex>{'n\\ge n_a:=\\frac{8}{\\Delta_a^2}\\ln\\frac{2Kn_a(n_a+1)}{\\delta}'}</Tex>. Hence total rollouts <Tex>{'\\le\\sum_a n_a=O\\!\\big(\\sum_a\\Delta_a^{-2}\\ln\\frac{K}{\\delta\\Delta_a}\\big)'}</Tex> with probability <Tex>{'\\ge1-\\delta'}</Tex>.</p>
            <Callout kind="warn">For <b>LUCB with our stack bound</b> no bound is proved here (<Badge kind="syn">empirical</Badge>). The literature bound for KL-LUCB (Kaufmann &amp; Kalyanakrishnan 2013, Thm 3) is <b>cited</b>, and applies to <em>their</em> exploration rate, not ours.</Callout>
          </Disclosure>
          <Disclosure title={<>Theorem 3 — validity of prefix reuse <Proved /></>}>
            <p>Let the process be Markov on time-augmented states, <Tex>{'Y'}</Tex> a function of the terminal state, and arm <Tex>{'j'}</Tex> defined by the start <Tex>{'(q_{j-1},j-1)'}</Tex> with first action <Tex>{'\\rho(q_{j-1})'}</Tex>. If a rollout of arm <Tex>{'i<j'}</Tex> visits <Tex>{'(j-1,q_{j-1})'}</Tex> and takes <Tex>{'\\rho(q_{j-1})'}</Tex>, then, conditionally on that event, its outcome is Bernoulli<Tex>{'(\\mu_j)'}</Tex> and independent of the earlier history.</p>
            <p><b>Proof.</b> The event is determined by the rollout up to and including its action at time <Tex>{'j-1'}</Tex> (a stopping-time event). By the strong Markov property the future after that action is independent of the past given (state, action), with exactly the law used by a direct pull of arm <Tex>{'j'}</Tex>. So matched observations of arm <Tex>{'j'}</Tex>, in collection order, are i.i.d. Bernoulli<Tex>{'(\\mu_j)'}</Tex> and the stack argument of Theorem 1 applies per arm; cross-arm dependence is handled by the union bound. ∎</p>
            <Callout kind="err" title="When it fails">Under state-reconstruction noise (A1 false) the replay context differs from the original, so sharing is disabled automatically. <b>Naive sharing</b> (credit every later arm) is invalid; the repository includes it only as a negative control and tests that its estimates are biased.</Callout>
          </Disclosure>
        </div>
      </Card></Reveal>

      <Reveal><div className="grid cols-2">
        <Card title="5 · Gaps, K and trajectory length">
          <ul className="small stack" style={{ paddingLeft: 18, margin: 0 }}>
            <li>Cost scales with the hardness <Tex>{'H=\\sum_a\\max(\\Delta_a,\\varepsilon/2)^{-2}'}</Tex>: the best-vs-second gap enters squared.</li>
            <li>More candidates <Tex>{'K'}</Tex> add arms and a <Tex>{'\\ln K'}</Tex> term; harmless steps are cheap to eliminate (large gap).</li>
            <li>Long trajectories add many near-identical early steps (all ≈ the re-roll baseline) — they are tied with each other but not with the best, which is fine for argmax certification.</li>
            <li>Prefix reuse changes the <em>effective</em> sample count per arm; the Experiment studio measures it.</li>
          </ul>
        </Card>
        <Card title="6 · Lower bound and ‘optimality’">
          <Tex block>{'\\mathbb E[\\tau]\\ \\ge\\ T^{*}(\\mu)\\,\\mathrm{kl}(\\delta,1-\\delta),\\qquad T^{*}(\\mu)^{-1}=\\sup_{w}\\inf_{\\lambda\\in\\mathrm{Alt}(\\mu)}\\sum_a w_a\\,d(\\mu_a,\\lambda_a)'}</Tex>
          <p className="small muted" style={{ marginBottom: 0 }}>(Garivier &amp; Kaufmann 2016, Thm 1; independent arms.) The repository computes <Tex>{'T^*'}</Tex> and plots it next to measured rollouts. We do <b>not</b> claim to match it and therefore never call AFCR “sample-optimal”.</p>
        </Card>
      </div></Reveal>

      <Reveal><Card title="7 · Claims ledger — what comes from where">
        <div className="tbl-wrap"><table className="tbl"><thead><tr><th className="wrap">Claim</th><th>Status</th><th className="wrap">Source</th></tr></thead><tbody>
          {([['Lower bound E[τ] ≥ T*(μ) kl(δ,1−δ)', 'cited', 'Garivier & Kaufmann 2016 (read)', 'info'], ['KL-LUCB δ-PAC with β(t,δ)=ln(k₁Ktᵅ/δ)+ln ln(·)', 'cited', 'Kaufmann & Kalyanakrishnan 2013, Thm 1 (read)', 'info'],
            ['Stack-KL confidence sequence is anytime-valid', 'proved', 'this work, Thm 1 (standard ingredients: stack model, Chernoff, union bound)', 'ok'], ['δ-correctness of the stopping rule for any sampling rule', 'proved', 'this work, Thm 1', 'ok'],
            ['Elimination sample complexity', 'proved', 'this work, Thm 2 (shape matches Even-Dar et al. 2006, abstract-level)', 'ok'], ['LUCB + stack-bound sample complexity', 'empirical', 'Experiment studio', 'syn'],
            ['Prefix reuse validity under Markov + exact match', 'proved', 'this work, Thm 3 + statistical unbiasedness tests', 'ok'], ['Pure exploration with side observations is a known setting', 'cited', 'Russo, Song & Pacchiano 2025 (abstract-level)', 'info'],
            ['Benefit on real LLM agents', 'hypothesis', 'ALFWorld / HotpotQA not run', 'pend'], ['Joint causes', 'not addressed', 'future work (GCJR, CAR-Shapley)', 'pend']] as const).map((r) => <tr key={r[0]}><td className="wrap">{r[0]}</td><td><Badge kind={r[3] as 'ok' | 'info' | 'syn' | 'pend'}>{r[1]}</Badge></td><td className="wrap">{r[2]}</td></tr>)}</tbody></table></div>
      </Card></Reveal>

      <Reveal><Card title="8 · Failure modes">
        <ul className="small stack" style={{ paddingLeft: 18, margin: 0 }}>
          <li><b>Ties / near-ties:</b> never certified at ε = 0 — the system abstains with a candidate set.</li>
          <li><b>Budget exhaustion:</b> an abstention. Reported separately from the error probability.</li>
          <li><b>Violated assumptions (A1–A6):</b> the guarantee is about the replay model, not the production system.</li>
          <li><b>Non-anytime intervals</b> (e.g. Wilson) or naive sharing: the guarantee flag turns off in the API response.</li>
          <li><b>Joint causes:</b> a single best step may not exist; the target is then not well-defined.</li>
        </ul>
      </Card></Reveal>
    </div>
  )
}
