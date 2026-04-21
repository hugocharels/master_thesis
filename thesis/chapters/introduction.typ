#import "@preview/dashy-todo:0.1.3": todo

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
goal - a setting that arises naturally in applications such as robot swarm coordination,
multi-robot task allocation, and cooperative strategy games.

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
supply a steady stream of novel levels during training, reducing the risk of overfitting to a
fixed set of hand-crafted scenarios and supporting generalisation across varied task structures.

The central difficulty in applying PCG to cooperative MARL is ensuring that generated environments
are meaningful: not only structurally well-formed, but genuinely solvable, and genuinely
cooperative. These are non-trivial requirements.

*Solvability* in a multi-agent setting is more demanding than in single-agent settings. It is not
sufficient for each agent to have a path to its goal; the agents must be able to reach their goals
simultaneously, following a joint sequence of actions that is consistent with all environmental
constraints, including dynamic elements whose state may depend on the current positions of other
agents. Testing whether such a joint solution exists is computationally non-trivial, and naively
generating random environments yields mostly unsolvable configurations, especially as the grid
size and number of agents grow.

*Cooperation* must be structurally enforced. A level that can be solved by agents acting
independently - without any agent ever assisting another - provides no training signal for
cooperative behaviour. For a level to serve as a useful cooperative training instance, it must
have the property that no agent can reach its goal unless at least one other agent performs a
supporting action. Simply generating solvable levels does not guarantee this: the generator must
be designed or constrained to produce configurations in which cooperation is a structural
necessity, not an option.

This thesis addresses both requirements together in a cooperative MARL environment introduced
later in the thesis. The key objective is not to design arbitrary random levels, but to generate
instances whose usefulness is supported by formal guarantees.


== Problem Statement, Research Questions, and Scope

The central problem this thesis addresses is the following: how can we automatically generate
levels for a cooperative MARL environment that are provably solvable and provably require
inter-agent cooperation?

We target two formal properties and one broader design objective. First, generated levels should
be solvable: the agents must admit at least one valid joint action sequence that completes the
task. Second, they should require cooperation: success should depend on agents supporting one
another rather than simply acting independently. Finally, the generated instances should remain
useful as potential training environments, although this thesis treats learnability as a design
objective rather than as a certified property.

More precisely, the work is organised around three research questions:

- *RQ1:* $dots$

#todo(position: "inline")[Add RQs]

The concrete benchmark used for this purpose is the Laser Learning Environment (LLE) @LLE,
introduced properly in the method chapter. The formal model focuses on the subset of its mechanics
needed for solvability and cooperation guarantees. The thesis does not claim to solve the
downstream MARL problem of training agents on the generated levels; its contribution is on the
generation and certification side.


== Thesis Structure

The remainder of this thesis is organised as follows.

- *Chapter 2 - State of the Art* #todo(position: "inline")[describe briefly]

- *Chapter 3 - Method* #todo(position: "inline")[describe briefly]

- *Chapter 4 - Experiments*
  - *Contributions* #todo(position: "inline")[describe briefly]
  - *Results* #todo(position: "inline")[describe briefly]

- *Chapter 5 - Conclusion and Future Work* #todo(position: "inline")[describe briefly]
