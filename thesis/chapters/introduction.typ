#import "@preview/dashy-todo:0.1.0": todo

== Context

Reinforcement Learning (RL) has established itself as a powerful paradigm for training autonomous
agents to make sequential decisions by interacting with an environment. In single-agent settings,
an agent repeatedly observes the state of the world, selects an action, and receives a scalar
reward signal that it tries to maximise over time. This framework has produced remarkable results
in domains ranging from board games to robotic control.

Multi-Agent Reinforcement Learning (MARL) extends this paradigm to settings in which several
agents act simultaneously within a shared environment. The agents may compete, cooperate, or
coexist independently, and their policies influence one another's learning dynamics. Cooperative
MARL, in particular, focuses on scenarios where a group of agents must jointly achieve a shared
goal - a setting that arises naturally in applications such as robot swarm coordination, multi-robot
task allocation, and cooperative strategy games.

Cooperative tasks introduce challenges that go beyond single-agent RL. Agents must not only
explore a potentially vast joint action space, but they must do so while accounting for the
behaviour of their teammates. Reward signals are often sparse: in many cooperative settings, the
team receives a reward only upon completing the full task, leaving agents with no intermediate
feedback to guide exploration. This makes the discovery of coordinated strategies especially
difficult when the required joint behaviour is long and precisely ordered.

A dimension of cooperative MARL that is frequently underestimated is the role of the training
environment itself. The structure of the levels or scenarios in which agents are trained directly
determines what coordination behaviours they can discover and practise. A poorly designed
environment - one that is unsolvable, trivially solvable by a single agent, or repetitive in
structure - yields limited training signal and constrains generalisation. Conversely, a
well-designed set of environments can expose agents to a rich variety of coordination challenges,
accelerate learning, and produce more robust policies. Designing such environments at scale,
however, is a labour-intensive process when done manually.


== Motivation

Procedural Content Generation (PCG) offers an alternative: the algorithmic, automatic creation of
environments according to user-defined criteria. Originally developed for video game level design,
PCG has since been applied to simulation-based agent training, where it enables the production of
large, diverse sets of environments without manual intervention. In the MARL context, PCG can
supply a steady stream of novel levels during training, reducing the risk of overfitting to a fixed
set of hand-crafted scenarios and supporting generalisation across varied task structures.

The central difficulty in applying PCG to cooperative MARL is ensuring that generated environments
are meaningful: not only structurally well-formed, but genuinely solvable, and genuinely
cooperative. These are non-trivial requirements.

*Solvability* in a multi-agent setting is more demanding than in single-agent settings. It is not
sufficient for each agent to have a path to its goal; the agents must be able to reach their goals
simultaneously, following a joint sequence of actions that is consistent with all environmental
constraints - including dynamic obstacles such as laser beams whose activity depends on the
current positions of other agents. Testing whether such a joint solution exists is computationally
non-trivial, and naively generating random environments yields mostly unsolvable configurations,
especially as the grid size and number of agents grow.

*Cooperation* must be structurally enforced. A level that can be solved by agents acting
independently - without any agent ever assisting another - provides no training signal for
cooperative behaviour. For a level to serve as a useful cooperative training instance, it must
have the property that no agent can reach its goal unless at least one other agent performs a
supporting action. Simply generating solvable levels does not guarantee this: the generator must
be designed or constrained to produce configurations in which cooperation is a structural
necessity, not an option.

This thesis addresses both requirements together. We focus on the Laser Learning Environment
(LLE) @LLE, a 2D grid-based cooperative benchmark for MARL, as our primary instantiation. LLE is
particularly well-suited to this study: its laser-blocking mechanics create precisely the kind of
inter-agent dependencies that make cooperation structurally necessary in certain configurations,
and its well-defined grid representation is amenable to formal analysis.


== Problem Statement

The central problem this thesis addresses is the following: how can we automatically generate LLE
levels that are provably solvable and provably require inter-agent cooperation?

We formalise three properties that a generated level should satisfy:

+ *Solvability* - the level admits at least one valid joint action sequence through which the agents
  collectively occupy all exit tiles. This is a necessary baseline: a level that cannot be
  completed is useless for training.

+ *Cooperation requirement* - the level cannot be solved without at least one agent performing
  a cooperative act (specifically, blocking a laser of its own colour to allow a teammate to
  pass). This property ensures that the level is not trivially solvable by independent agent
  behaviour.

+ *Learnability* - the solution is discoverable by MARL algorithms through exploration. While
  solvability and cooperation can be verified formally, learnability depends on the agent
  architecture, the reward structure, and the exploration strategy, and remains an open problem
  outside the scope of this thesis. We treat it as a desirable property and discuss it in terms
  of structural affordances that facilitate discovery.

The approach we adopt to address the first two properties is a reduction to Boolean
Satisfiability (SAT): we encode the constraints of the LLE level as a propositional formula in
conjunctive normal form (CNF), and delegate the solvability check to a modern SAT solver. The
cooperation property is detected via a second SAT call on a stricter variant of the encoding.
Both calls are embedded in a generation loop that produces levels until the desired properties
are satisfied.


== Contributions

This thesis makes the following contributions:

- *A SAT-based solver for bounded-horizon LLE solvability.* We provide a CNF encoding of
  the LLE decision problem over a bounded time horizon $T$. Given a level and a horizon, the
  solver returns SAT (with a satisfying assignment that encodes a valid joint trajectory) or UNSAT
  (certifying that no solution exists within $T$ steps). The encoding is described in full in
  <sat-reduction>.

- *A formal cooperation detector.* We define a strict variant of the LLE semantics in which
  agents can no longer block beams of their own colour, thereby removing the
  laser-blocking action through which agents help one another. We prove that a level requires
  cooperation if and only if the standard encoding is satisfiable and the strict encoding is
  unsatisfiable. This gives a decision procedure for the cooperation property based on two SAT
  calls (<cooperation-detection>).

- *A first family of procedural level generators.* Building on the solver and cooperation detector,
  we implement several generators, including random solvable, constrained random solvable, random
  cooperative, and constrained random cooperative variants. Each accepted level is certified by the
  solver to satisfy the advertised properties of its output (<generators>). #todo(position: right)[specify all generators]

- *An empirical comparison of two SAT formulations.* We compare two alternative encodings of the
  agent-uniqueness constraint, measuring their effect on CNF size and solver runtime
  (<benchmarking>, <experiments>). #todo(position: right)[Which experiments I did]

The approach developed here is specific to LLE in its SAT encoding - the laser mechanics,
colour-matching rules, and exit conditions are all embedded in the formula structure. However,
the broader methodology - reducing solvability and cooperation to formal properties, verifying
them via a constraint solver, and embedding the verifier in a generation loop - is general and
can be adapted to other grid-based cooperative MARL environments, provided an appropriate
encoding is designed for the target environment.


== Thesis Structure

The remainder of this thesis is organised as follows.

*Chapter 2 — Background* introduces the technical foundations needed to follow the thesis:
the MARL framework and its cooperative variant, a detailed description of the Laser Learning
Environment, an overview of Procedural Content Generation and its main paradigms, and an
introduction to Boolean Satisfiability including its complexity-theoretic role in the context
of LLE.

*Chapter 3 — Related Work* #todo(position: right)[ADD]

*Chapter 4 — Methods* is the core of the thesis. It formalises the LLE level structure,
solvability, and cooperation requirement; presents the full SAT encoding and its correctness
argument; introduces the cooperation detection theorem and its proof; describes the four
generators; and defines the benchmarking protocol. #todo(position: right)[ADD]

*Chapter 5 — Experiments* presents the empirical results: solver performance, generator
acceptance rates, cooperation rates, and level diversity across a range of configurations.
#todo(position: right)[ADD]

*Chapter 6 — Conclusion* #todo(position: right)[ADD]
