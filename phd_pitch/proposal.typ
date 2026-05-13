#set page(paper: "a4", margin: (x: 2.5cm, y: 2.5cm))
#set text(font: "New Computer Modern", size: 11pt, lang: "en")
#set par(justify: true, leading: 0.65em, first-line-indent: 0pt)
#show heading.where(level: 1): it => block(above: 1.5em, below: 0.7em)[
  #text(size: 15pt, weight: "bold")[#it.body]
]
#show heading.where(level: 2): it => block(above: 1.1em, below: 0.45em)[
  #text(size: 12pt, weight: "bold")[#it.body]
]
#show heading.where(level: 3): it => block(above: 0.8em, below: 0.3em)[
  #text(size: 11pt, weight: "bold", style: "italic")[#it.body]
]

#align(center)[
  #text(size: 18pt, weight: "bold")[PhD Proposal --- Discussion Notes]
  #v(0.3em)
  #text(size: 12pt)[Hugo Charels --- 12 May 2026]
  #v(0.2em)
  #text(size: 10pt, style: "italic")[Pre-meeting notes for Tom Lenaerts]
]

#v(1em)

= Framing

My master's thesis built a SAT-based generator for the Laser Learning
Environment (LLE) that produces levels with _certified solvability_ and a
precise definition of _cooperation requirement_ (standard solver SAT and
strict-laser solver UNSAT). The infrastructure --- the solver--generator
infrastructure, the modular constraint system, multiple generation strategies, and a
benchmark suite --- is a re-usable platform rather than a one-off prototype.

The natural PhD question is therefore not "what else can we generate?" but:
_what new science does certified procedural generation enable for cooperative
multi-agent reinforcement learning?_

Multi-agent RL currently lacks controlled distributions: benchmarks are
hand-crafted, "cooperation" is defined informally per environment, and we cannot
cleanly disentangle algorithmic ability from benchmark idiosyncrasy. Formal
methods can plausibly fix this. Below are three directions, ordered from most
incremental to most ambitious, each framed as a 3--4 paper PhD arc.

= Direction A --- Formally-verified curricula for cooperative MARL

== Problem

MARL training relies on hand-tuned curricula whose properties (difficulty,
cooperation requirement, distribution shift) are observed _post hoc_ rather
than guaranteed by construction. This makes curriculum studies hard to
reproduce and harder to interpret: when an algorithm fails on a new
benchmark, we cannot tell whether the algorithm or the curriculum is at
fault.

== Approach

Re-introduce a world-data abstraction beyond LLE so the SAT encoding
becomes a domain-agnostic _property certifier_ for grid-based MARL
environments. Use the resulting generator as a curriculum source with formally
controlled axes: minimum path length, agent coupling, hazard density,
cooperation degree, and so on. Every level in a training distribution would
carry a certificate of its properties.

== Concrete contributions

+ A domain-agnostic SAT encoding for solvability and cooperation in
  grid-MARL, validated by adapters for at least two benchmarks (LLE and one
  Overcooked-style environment).
+ An empirical study: do agents trained on certified-cooperation curricula
  develop more cooperative policies than those trained on randomly generated
  curricula of matched difficulty?
+ A held-out generalization protocol: train on a certified distribution,
  evaluate on certified out-of-distribution test sets. This is something
  currently impossible in MARL because there is no notion of "controlled
  distribution shift" for hand-crafted environments.
+ (Optional fourth paper.) A benchmark + leaderboard built on the certified
  generator, with reproducibility guarantees.

== Why it works

It builds directly on the existing code base, each contribution is a
publishable paper on its own, and risk is low because the master thesis
already proves the core technique works.

== Risk

It may be perceived as engineering rather than science. Counter by leading
the pitch with the empirical questions (paper 2 and paper 3), not the
framework.

= Direction B --- Quantifying cooperation: from binary to spectrum

== Problem

"Cooperation" in MARL is currently defined informally and per-environment.
My thesis already operates with a binary definition (a level needs
cooperation or it does not). This is a useful starting point but inadequate
for studying _how_ and _how much_ agents cooperate, which is precisely the
question that makes cooperation interesting in the first place.

== Approach

Develop a multi-dimensional formal theory of cooperation. Candidate
dimensions include:

- _Degree_: minimum number of jointly-required actions on any solving
  trajectory.
- _Asymmetry_: distribution of necessary actions across agents (does one
  agent do all the work, or is the load balanced?).
- _Temporal coupling_: width of the synchronization window between
  cooperative actions.
- _Information dependence_: does cooperation require explicit communication,
  or is shared observation sufficient?

Each dimension can be encoded as a SAT or SMT property and decided
automatically on a generated environment. The generator can then _target_
specific cooperation profiles, allowing controlled experiments that are
currently impossible.

== Concrete contributions

+ A formal taxonomy of cooperation properties, with SAT/SMT-based decision
  procedures and complexity analysis.
+ An empirical census: across existing MARL benchmarks (LLE, SMAC,
  Overcooked, Hanabi, ...), what cooperation profiles do they actually
  exhibit? This may produce surprising results --- the field assumes its
  benchmarks cover cooperation broadly, but they may all live in a narrow
  region of the spectrum.
+ A controlled experiment: do current MARL algorithms (QMIX, MAPPO, MADDPG)
  generalize across cooperation types, or do they specialize on the profiles
  they were trained on?
+ A targeted-generation study showing that algorithm rankings depend on the
  cooperation profile of the test set --- a benchmarking critique with
  methodological consequences.

== Why it works

This is the direction with the most theoretical originality and the most
direct connection to long-standing questions in cooperation science. It
re-frames the thesis as a contribution to the _theory of cooperation_, with
formal methods as the instrument and MARL as the empirical playground. It is
also the direction most likely to interest groups working on the evolution of
cooperation.

== Risk

Defining the right dimensions is hard, and the taxonomy might not survive
contact with reality. Mitigate by anchoring each dimension in a concrete
game-theoretic intuition (e.g. asymmetry maps to load distribution in public
goods games) and by validating empirically that each dimension actually
discriminates between known benchmarks.

= Direction C --- Neuro-symbolic MARL: the solver as training oracle

== Problem

Reinforcement learning agents discover cooperation through trial and error,
often inefficiently. The SAT solver, however, can answer counterfactual
questions about a state in milliseconds: "is this state still jointly
solvable?", "which agent's next action narrows the cooperation window most?",
"how much slack does this trajectory have before becoming unsolvable?". This
information is currently thrown away.

== Approach

Inject solver-derived signals directly into the training loop. Three
candidate uses:

- _Reward shaping_ proportional to remaining solvability margin.
- _Intrinsic motivation_ derived from cooperation-criticality of visited
  states.
- _Curriculum_ that progressively shrinks the slack between feasible and
  infeasible trajectories.

== Concrete contributions

+ A neuro-symbolic training framework where a SAT/SMT oracle provides dense
  feedback to MARL agents, with engineering attention paid to incremental
  solving.
+ Sample-efficiency studies on LLE and at least one other benchmark,
  demonstrating measurable gains over baselines.
+ A theoretical characterization of which solver signals are useful and when
  they degenerate into reward hacking or shortcut exploitation.
+ (Optional.) Learned approximations of the solver oracle (a "neural
  solvability head") to reduce inference cost at training scale.

== Why it works

Connects the thesis to the active neuro-symbolic AI agenda; offers a clear
empirical hook (sample efficiency) that referees consistently reward; and
keeps the SAT machinery at the centre of the methodology rather than
relegating it to data generation.

== Risk

Solver calls can be expensive at training scale; engineering effort is
non-trivial. Tractability hinges on incremental SAT, caching, or learned
approximations. There is also a methodological risk of "smuggling the answer
into the reward" --- handle this with careful baselines.

= Discussion points for the meeting

- Which direction best aligns with the group's current interests ---
  cooperation theory (B), MARL methodology (A), or neuro-symbolic methods
  (C)?
- Is there an existing collaboration (with Yannick, with other group
  members, or external) that would strengthen one of these directions?
- Funding fit: would FRIA/FNRS be the natural route, or an assistantship at
  MLG? The two have different selection cycles and obligations.
- What would constitute a credible _first paper_ within the first
  12 months, given each direction?
- A possible hybrid: start in Direction A (low-risk consolidation of the
  master's work) and pivot toward B or C in years 2--3 once the
  infrastructure paper is published.
