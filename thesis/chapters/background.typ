== Multi-Agent Reinforcement Learning

Multi-Agent Reinforcement Learning (MARL) extends Reinforcement Learning to settings in which
$n >= 2$ agents act simultaneously within a shared environment. A standard formalisation is the
stochastic game introduced by Shapley @Shapley1953 and widely used as a foundation for MARL
@Littman1994. The model is given by the tuple
$(X, {U^i}_(i=1)^n, T, {R^i}_(i=1)^n, gamma)$, where $U^i$ is the action space of agent $i$ and
$R^i$ is its reward function. At each time step, every agent selects an action independently, the
joint action $bold(u)_t = (u_t^1, ..., u_t^n)$ determines the state transition, and each agent
receives a reward.

This thesis concerns the fully cooperative setting, where all agents share a single reward signal:
$R^1 = R^2 = ... = R^n = R$. The difficulty in this setting is not only to find good individual
actions, but to discover joint behaviour that is useful at the team level. In sparse-reward tasks,
supportive actions may carry no immediate local benefit, which makes them difficult to learn from
experience alone.


== The Laser Learning Environment

The Laser Learning Environment (LLE) @LLE is a 2D grid-based cooperative puzzle game designed as a
benchmark for MARL algorithms. It supports between one and four agents and is built around a set
of mechanics that make cooperative coordination both necessary and difficult to learn.


=== Structure and Mechanics

An LLE level is played on a rectangular grid of height $H$ and width $W$. Each cell is either a
floor tile, a wall, a laser source, or an exit. The key components are as follows.

*Agents.* Each agent is assigned a unique colour from the set $C = {0, 1, ..., n_a - 1}$. At the
start of an episode, agent $c$ is placed at its designated starting cell $s(c)$. At each time
step, an agent may stay in place or move to an adjacent non-wall cell. Agents cannot occupy the
same cell simultaneously.

*Lasers.* Each laser source $(c, d, p) in cal(S)$ emits a beam of colour $c$ in direction
$d in {N, S, E, W}$ starting from cell $p$. The beam propagates cell by cell in direction $d$
until it is blocked by a wall or by an agent of the same colour. Any agent of a different colour
that enters a traversed cell is eliminated. This creates a direct dependency between colours:
each beam can be neutralised only by the matching agent.

*Exits.* A level contains exactly $n_a$ exit tiles. The episode is completed successfully when all
exit tiles are occupied simultaneously. Since agents cannot share positions, this means that each
exit is occupied by exactly one agent in a winning configuration.

*Zero-incentive bottlenecks.* Intermediate cooperative acts, such as blocking a beam for a
teammate, carry no immediate reward. The reward is issued only when all agents complete the level.
An agent may therefore need to take a locally useless action that is beneficial only to the team,
which makes exploration difficult @LLE.

The full LLE implementation contains additional mechanics that are not modelled in this thesis,
such as gems and void tiles. We omit them because they are not needed for the bounded solvability
questions studied here. In particular, void tiles can be conservatively replaced by walls when
constructing instances for the current solver.


=== An Illustrative Example

#figure(
  image("../../assets/lvl6-annotated.png", width: 65%),
  caption: [
    An annotated LLE level. Laser beams (coloured lines) block movement for agents of a different
    colour. The yellow agent blocks the yellow laser to allow the other agents to pass.
  ],
)

The figure above illustrates a typical LLE dependency. One agent must occupy the path of its own
laser so that the beam is truncated and another agent can pass. This is the type of blocking-based
cooperation studied throughout the rest of the thesis.


=== Relevance as a Benchmark

LLE has been used to evaluate several value-based MARL algorithms, including methods augmented
with prioritised experience replay, $n$-step returns, and intrinsic curiosity via random network
distillation @LLE. Despite these enhancements, agents frequently fail to escape coordination
bottlenecks in LLE, even when they perform well on more conventional cooperative benchmarks.

For that reason, LLE is a suitable benchmark for studying whether formally constrained generation
can produce levels that are both solvable and structurally cooperative.


== Procedural Content Generation

Procedural Content Generation (PCG) refers to the algorithmic creation of content such as levels,
maps, or environments with limited direct human input @Shaker2016. In the MARL setting, PCG is
valuable because it can supply a large and diverse stream of training instances instead of relying
on a small fixed set of hand-crafted levels.

PCG methods are commonly grouped into three families. *Constructive methods* generate content in a
single forward pass and are typically fast, but offer no formal guarantees. *Search-based methods*
treat generation as an optimisation problem guided by a fitness function @Togelius2011. They can
express rich objectives, but they inherit the limitations of the chosen heuristic. *Constraint-based
methods* encode desired properties explicitly and use a solver to find content satisfying them.

This thesis adopts the constraint-based paradigm because the target properties are logical rather
than purely stylistic: we want accepted levels to come with formal guarantees of solvability and
cooperation.


== Boolean Satisfiability

The Boolean Satisfiability problem (SAT) is the canonical NP-complete decision problem. Given a
propositional formula $phi$ over a set of Boolean variables $x_1, ..., x_n$, the question is:
does there exist a truth assignment $nu : {x_1, ..., x_n} -> {"true", "false"}$ such that
$phi(nu) = "true"$? The central role of SAT in complexity theory was established by the
Cook-Levin theorem @Cook1971.

SAT solvers typically operate on formulas in *Conjunctive Normal Form* (CNF), where a formula is
represented as a conjunction of clauses and each clause is a disjunction of literals:

$
  phi = and.big_(i=1)^m or.big_(j) ell_(i,j)
$

Any propositional formula can be converted to an equisatisfiable CNF formula in polynomial time.
When a CNF formula is satisfiable, a solver returns a satisfying assignment; otherwise it returns
UNSAT.

Modern SAT solvers, especially CDCL-based solvers, often perform very well on large structured
instances in practice. This empirical effectiveness is what makes SAT a plausible backend for the
solvability and cooperation checks developed in this thesis.
