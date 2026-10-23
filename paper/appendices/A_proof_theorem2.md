# Appendix A. Proof of Theorem 2 (successive elimination)

*Extracted from `paper/main.md` by `scripts/build_appendices.py`; edit the paper, not this file.*


**Algorithm.** Pull every unseen arm once; thereafter pull, one at a time, the surviving arm with the fewest observations (ties by index), where an arm $a$ is *eliminated* once $\mathrm{hi}_a<\max_b\mathrm{lo}_b$ (running-intersection intervals). Stop at the first time $\mathrm{lo}_h>\max_{a\ne h}\mathrm{hi}_a$ (ε = 0). Sharing is off, so survivors always have equal counts at the end of a round.

**Half-width.** By Pinsker's inequality $\mathrm{kl}(p,q)\ge2(p-q)^2$, hence $B_{a,n}\subseteq[\hat\mu-w_n,\hat\mu+w_n]$ with $w_n=\sqrt{x_n/(2n)}$. On $E$, $|\hat\mu_{a,n}-\mu_a|\le w_n$, so $B_{a,n}\subseteq[\mu_a-2w_n,\mu_a+2w_n]$, and the running intersection can only shrink the interval.

**The best arm is never eliminated.** On $E$, $\mathrm{hi}_{a^\star}\ge\mu^\star\ge\mu_b\ge\mathrm{lo}_b$ for every $b$, so $\mathrm{hi}_{a^\star}<\max_b\mathrm{lo}_b$ never holds; $a^\star$ is pulled in every round and has $n$ observations after round $n$.

**Elimination time.** Fix $a\ne a^\star$ and let $n_a=\min\{n:\,4w_n<\Delta_a\}$; since $4w_n<\Delta_a\iff n>8x_n/\Delta_a^2$ this is the $n_a$ of the statement. If $a$ is still active after round $n_a$, then $\mathrm{hi}_a\le\mu_a+2w_{n_a}<\mu^\star-2w_{n_a}\le\mathrm{lo}_{a^\star}$, so $a$ is eliminated. Hence $a$ is pulled at most $n_a$ times.

**The stopping rule fires.** Let $N^\star$ be the number of observations of $a^\star$ and suppose $N^\star\ge n_{\max}=\max_an_a$. For every other arm $a$, either (i) $a$ was pulled $n_a$ times, so $\mathrm{hi}_a<\mathrm{lo}_{a^\star}$ as just shown, or (ii) $a$ was eliminated earlier because $\mathrm{hi}_a(t_a)<\mathrm{lo}_{b}(t_a)$ for some arm $b$ at that time. In case (ii), $\mathrm{lo}_b(t_a)\le\mu_b\le\mu^\star-\Delta_b$ if $b\ne a^\star$, and $N^\star\ge n_{\max}\ge n_b$ gives $2w_{N^\star}<\Delta_b/2$, so $\mathrm{lo}_{a^\star}\ge\mu^\star-2w_{N^\star}>\mu^\star-\Delta_b\ge\mathrm{lo}_b(t_a)>\mathrm{hi}_a$; if $b=a^\star$, monotonicity of the running intersection gives $\mathrm{lo}_{a^\star}(\text{now})\ge\mathrm{lo}_{a^\star}(t_a)>\mathrm{hi}_a$. So $\mathrm{lo}_{a^\star}>\mathrm{hi}_a$ for all $a\ne a^\star$ and the stopping rule has fired by the end of round $n_{\max}$.

**Count.** Arm $a^\star$ is pulled at most $n_{\max}$ times and each other arm at most $n_a$ times, giving the stated total. Finally $n_a\le 1+\frac8{\Delta_a^2}\ln\frac{2Kn_a(n_a+1)}{\delta}$, whose solution is $O(\Delta_a^{-2}\ln(K/(\delta\Delta_a)))$. ∎
