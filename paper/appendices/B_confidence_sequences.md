# Appendix B. Notes on the confidence sequences

*Extracted from `paper/main.md` by `scripts/build_appendices.py`; edit the paper, not this file.*


The stack-KL interval is obtained by bisection on $n\,\mathrm{kl}(\hat\mu,q)\le x_n$; the returned end of the final bracket is the *conservative* one (the side on which the KL exceeds the radius), so the computed interval always contains the exact KL ball. A radius of $+\infty$ (no observations) gives $[0,1]$. A pure-Python scalar path is used for small arrays (identical semantics, about 25× faster than the vectorised path for per-pull updates).
