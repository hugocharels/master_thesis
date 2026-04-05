== Multi-Agent Reinforcement Learning

=== Single-Agent Reinforcement Learning

Reinforcement Learning (RL) is a framework for sequential decision-making in which an agent
interacts with an environment over a series of discrete time steps. At each step $t$, the agent
observes a state $s_t$ from the state space $cal(S)$, selects an action $a_t$ from its action
space $cal(A)$, and receives a scalar reward $r_t in RR$ from the environment. The environment
then transitions to a new state $s_(t+1)$ according to a transition function
$T : cal(S) times cal(A) -> Delta(cal(S))$, where $Delta(cal(S))$ denotes the set of probability
distributions over $cal(S)$. This structure defines a Markov Decision Process (MDP), characterised
by the tuple $(cal(S), cal(A), T, R, gamma)$, where $R : cal(S) times cal(A) -> RR$ is the reward
function and $gamma in [0, 1)$ is a discount factor controlling the relative weight of future
rewards.

The agent's goal is to learn a policy $pi : cal(S) -> Delta(cal(A))$ that maximises the expected
discounted cumulative reward, or return:

$
  G_t = sum_(k=0)^(infinity) gamma^k r_(t+k)
$

RL algorithms differ in how they estimate and optimise this objective — through value function
approximation (Q-learning, DQN), policy gradient methods (REINFORCE, PPO), or actor-critic
architectures — but all share the same underlying MDP structure.


=== Extension to Multiple Agents

Multi-Agent Reinforcement Learning (MARL) extends the single-agent framework to settings
involving $n >= 2$ agents acting simultaneously within a shared environment. The standard
formalisation is the Markov Game (also called a Stochastic Game), defined by the tuple
$(cal(S), {cal(A)^i}_(i=1)^n, T, {R^i}_(i=1)^n, gamma)$, where $cal(A)^i$ is the action space
of agent $i$ and $R^i$ is its individual reward function. At each time step, every agent selects
an action independently, the joint action $bold(a)_t = (a_t^1, ..., a_t^n)$ determines the state
transition and each agent's reward.

Depending on the structure of the reward functions, Markov Games span a spectrum from fully
competitive (zero-sum games, where agents' interests are directly opposed) to fully cooperative
(team games, where all agents share the same reward). Intermediate settings — with a mix of
individual and shared incentives — also arise in practice. This thesis focuses exclusively on the
cooperative setting.

In cooperative MARL, all agents share a single reward signal: $R^1 = R^2 = ... = R^n = R$. The
team's objective is to find a joint policy $bold(pi) = (pi^1, ..., pi^n)$ that maximises the
shared return. Cooperation is thus not assumed but must emerge from learning: agents must
discover that coordinating their actions leads to higher team rewards than acting independently.


=== Challenges in Cooperative MARL

Cooperative MARL introduces a set of challenges that are absent or less severe in single-agent
settings.

*Non-stationarity.* From the perspective of any individual agent, the environment appears
non-stationary: other agents are simultaneously updating their policies, causing the effective
dynamics observed by each agent to change over time. This violates the stationarity assumption
underlying most single-agent RL theory and can destabilise learning.

*Exponential joint action space.* The joint action space grows exponentially in the number of
agents. Even when each agent has a small individual action space, the number of possible joint
actions becomes intractable for large teams. This makes centralised control infeasible and
motivates decentralised execution paradigms.

*Credit assignment.* When agents share a single reward signal, attributing each agent's
contribution to the team outcome becomes difficult. Poor credit assignment leads to agents
converging to suboptimal policies in which some agents free-ride on the efforts of others.

*Sparse rewards and exploration.* In many cooperative tasks, the team reward is issued only
upon completing the full task. Agents must therefore explore long sequences of joint actions
without intermediate feedback. In environments where the rewarding joint behaviour is rare or
precisely ordered, pure random exploration is ineffective and training can stall entirely.

This last challenge is particularly acute in environments like LLE, where agents must execute
carefully synchronised cooperative sequences with no intermediate reward — a setting known as
the zero-incentive bottleneck problem, described in the following section.


== The Laser Learning Environment

The Laser Learning Environment (LLE) <LLE> is a 2D grid-based cooperative puzzle game designed
as a benchmark for MARL algorithms. It supports between one and four agents and is built around
a set of mechanics that make cooperative coordination both necessary and difficult to learn.


=== Structure and Mechanics

An LLE level is played on a rectangular grid of height $H$ and width $W$. Each cell is either
a floor tile, a wall, a laser source, or an exit. The key components are as follows.

*Agents.* Each agent is assigned a unique colour from the set $cal(A)$. At the start of an
episode, agent $c$ is placed at its designated starting cell $s(c)$. At each time step, an agent
may stay in place or move to an adjacent non-wall cell. Agents cannot occupy the same cell
simultaneously.

*Lasers.* Each laser source $(c, d, p) in cal(S)$ emits a beam of colour $c$ in direction
$d in {N, S, E, W}$ starting from cell $p$. The beam propagates cell by cell in direction $d$
until it is blocked by a wall or, crucially, by an agent. The key mechanic governing laser
interaction is *colour matching*: a beam of colour $c$ is blocked only by an agent of colour $c$.
Any agent of a different colour that enters a cell traversed by a beam of colour $c$ is eliminated.
This creates a strict interdependency: each laser can only be neutralised by one specific agent.

*Exits.* Each agent $c$ has a designated exit cell $cal(E)(c)$. The episode is completed
successfully when every agent occupies its exit cell simultaneously. This synchronisation
requirement prevents agents from solving the level independently: an agent that reaches its exit
early must remain there, possibly blocking other agents, until all teammates arrive.

*Zero-incentive bottlenecks.* A distinctive property of LLE is that intermediate cooperative
acts — such as positioning to block a laser for a teammate — carry no immediate reward. The
reward is issued only when all agents complete the level. An agent that sacrifices its own
optimal path to assist a teammate receives no direct signal that this behaviour is beneficial.
This creates exploration bottlenecks: agents have no local incentive to adopt cooperative
strategies, and discovering the required joint behaviour through random exploration is
exceedingly unlikely, especially in larger levels.


=== An Illustrative Example

#figure(
  image("../../assets/lvl6-annotated.png", width: 65%),
  caption: [
    An annotated LLE level. Each agent must reach the exit of its own colour. Laser beams
    (coloured lines) block movement for agents of a different colour. Agent 0 (blue) must
    block the blue laser to allow agent 1 (orange) to pass — a cooperative act that yields
    no intermediate reward.
  ],
)

The figure above illustrates a typical LLE level. The blue agent must position itself in the
path of the blue laser, blocking it so that the orange agent can pass through cells the beam
would otherwise reach. This blocking act is purely beneficial to the orange agent: the blue
agent is immune to its own laser and gains nothing directly from the manoeuvre. The level
cannot be completed without this cooperative step, yet no reward is given for performing it.


=== Relevance as a Benchmark

LLE has been used to evaluate several state-of-the-art value-based MARL algorithms, including
methods augmented with prioritised experience replay, $n$-step returns, and intrinsic curiosity
via random network distillation <LLE>. Despite these enhancements, agents frequently fail to
escape coordination bottlenecks in LLE, even when they achieve near-perfect coordination in
more conventional cooperative benchmarks.

This combination of properties — formal solvability structure, strict coordination requirements,
sparse rewards, and zero-incentive bottlenecks — makes LLE an ideal environment for studying
the relationship between level design and agent learning. It is the primary instantiation of
our framework, though the methodology developed here is designed with generalisability to other
grid-based cooperative environments in mind.


== Procedural Content Generation

Procedural Content Generation (PCG) refers to the algorithmic creation of content — levels,
maps, textures, narratives, or entire game worlds — with limited or no direct human input. PCG
has a long history in game development, where it serves to increase replayability, reduce
production costs, and produce content at scales that manual design cannot achieve. More
recently, PCG has been adopted in simulation-based agent training as a way to supply diverse
and varied environments during learning.

PCG methods can be broadly organised into three paradigms.

*Constructive methods* generate content in a single forward pass, without backtracking or
verification. Examples include noise-based generators (Perlin noise, cellular automata) that
produce cave-like or organic layouts, grammar-based systems that expand structural rules into
level geometry, and Wave Function Collapse, which tiles levels from locally consistent
patterns. Constructive methods are fast and scalable, but offer no formal guarantees: a
generated level may be unsolvable, disconnected, or trivially easy.

*Search-based methods* frame content generation as an optimisation problem and explore the
space of possible levels using heuristic search or evolutionary algorithms. A fitness function
evaluates candidate levels against desired properties — solvability, playability, difficulty —
and the search is guided toward high-fitness regions. Search-based methods can incorporate
complex objectives but are computationally expensive and depend heavily on the quality of the
fitness function.

*Constraint-based methods* encode the desired properties of the content as a constraint
satisfaction problem (CSP) or a propositional formula, and use a solver to find a level that
satisfies all constraints. This approach offers formal guarantees: if a solution is found, it
is certified to satisfy every specified property. The cost is the computational overhead of
solving the constraint system, which grows with the complexity of the level.

This thesis adopts the constraint-based paradigm, using Boolean Satisfiability as the
underlying solver. The choice is motivated by the need for formal solvability and cooperation
guarantees — properties that constructive and search-based methods cannot provide directly.


== Boolean Satisfiability

=== The SAT Problem

The Boolean Satisfiability problem (SAT) is the canonical NP-complete decision problem. Given
a propositional formula $phi$ over a set of Boolean variables $x_1, ..., x_n$, the question
is: does there exist a truth assignment $nu : {x_1, ..., x_n} -> {"true", "false"}$ such that
$phi(nu) = "true"$?

SAT solvers operate on formulas in *Conjunctive Normal Form* (CNF): a conjunction of clauses,
where each clause is a disjunction of literals (a variable or its negation):

$
  phi = and.big_(i=1)^m or.big_(j) ell_(i,j)
$

Any propositional formula can be converted to an equisatisfiable CNF formula in polynomial
time using the Tseitin transformation. When a formula is satisfiable, a solver returns a
satisfying assignment (a *model*); when it is not, it returns UNSAT with a proof of
unsatisfiability.


=== Modern SAT Solvers

Early SAT solvers were based on the Davis-Putnam-Logemann-Loveland (DPLL) algorithm, a
backtracking search procedure augmented with unit propagation and pure literal elimination.
Modern solvers implement Conflict-Driven Clause Learning (CDCL), which extends DPLL with
two key innovations: *clause learning* (recording the reason for each conflict as a new clause,
preventing the solver from revisiting the same conflict) and *non-chronological backtracking*
(jumping back further in the search tree based on the learned clause). CDCL solvers also
employ sophisticated heuristics for variable ordering and restart policies that dramatically
reduce the search space in practice.

Despite SAT being NP-complete in the worst case, modern CDCL solvers routinely handle
industrial instances with millions of variables and clauses within seconds. This empirical
tractability is the primary motivation for using SAT as the backend for our solvability
checker.


=== Complexity of LLE Solvability

The SAT problem is NP-complete by the Cook-Levin theorem <Cook1971>: every problem in NP can
be reduced to SAT in polynomial time, and SAT is itself in NP. This places SAT at the
boundary of what is efficiently verifiable but not (provably) efficiently solvable in the
worst case.

The solvability problem for LLE — given a level $L$ and a time horizon $T$, does a valid
joint trajectory of length at most $T$ exist? — is in *NP*: a candidate trajectory can be
verified in polynomial time by simulating the joint execution and checking that all agents
reach their exits without violating any constraint.

The reduction we present in <sat-reduction> encodes this problem as a CNF formula in
polynomial time with respect to the level parameters ($H$, $W$, $|cal(A)|$, $T$). This
establishes that LLE solvability is polynomial-time many-one reducible to SAT:

$
  "LLE-Solvability" <=_p "SAT"
$

This means LLE solvability is *at most as hard as SAT*: any algorithm for SAT immediately
yields an algorithm for LLE solvability with only polynomial overhead.

Whether LLE solvability is *NP-hard* — i.e., whether SAT is also reducible to LLE — remains
an *open question*. Establishing NP-hardness would require constructing a polynomial-time
reduction from an NP-hard problem (such as SAT or 3-SAT) to LLE solvability, showing that
LLE solvability encodes arbitrary constraint satisfaction. Such a result would place LLE
solvability in the class of NP-complete problems, meaning it is among the hardest problems in
NP and no polynomial-time algorithm exists unless P = NP.

In any case, the practical consequence of the reduction is clear: our SAT-based solver
inherits the strong empirical performance of modern CDCL solvers, making it effective on
the LLE instances encountered in practice, even if the worst-case complexity is high.
