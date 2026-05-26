// Document settings

#set page(
  number-align: center,
)
#set heading(
  numbering: "1.1",
)

#set text(lang: "en")
#set par(justify: true)

// Make `@label` to a depth-1 heading render as "Chapter N" instead of the
// default "Section N", so cross-references between chapters click through
// to the right place and read naturally.
#show heading.where(level: 1): set heading(supplement: [Chapter])

#show heading: it => {
  if it.depth == 1 {
    let chapter_num = counter(heading.where(level: 1)).at(it.location()).at(0)

    if { 0 < chapter_num and chapter_num < 8 } {
      pagebreak()
      v(100pt)

      let chapter = text(strong("Chapter " + str(chapter_num)), 22pt)
      let content = text(strong(it.body), 30pt)
      chapter + [ \ \ ] + content + [ \ \ ]
    } else {
      if it.body == [Conclusion] or it.body == [Appendix] {
        pagebreak()
        v(100pt)

        let content = text(strong(it.body), 30pt)
        content + [ \ \ ]
      } else {
        it
      }
    }
  } else {
    [ \ ] + it
    v(10pt)
  }
}

// Cover page

#text(14pt)[Faculty of Sciences #h(1fr) Department of Computer Sciences]

#v(10pt)

#align(
  center,
  [#image("../assets/logos/sceau-a-quadri.jpg", width: 50%)],
)

#v(10pt)

#align(center, text(14pt)[
  #smallcaps("Master thesis")
])

#v(10pt)

// The curriculum-transfer experiments did not produce a positive result
// (see @transfer-experiment), so the title reflects the certified-generation
// contribution rather than curriculum learning. The curriculum-in-the-title
// variant is kept here for reference:
//
//   Procedural Generation of Solvable Cooperative Levels
//   for Curriculum Learning in the Laser Learning Environment
#align(center, text(18pt)[
  *Procedural Generation of Solvable Cooperative Levels \
  for the Laser Learning Environment*
])

#v(10pt)

#grid(
  columns: (1fr, 1fr),
  align(center)[
    *Author:* \
    Hugo Charels \
    #link("mailto:hugo.charels@ulb.be")
  ],
  align(center)[
    *Supervisors:* \
    Tom Lenaerts \
    Yannick Molinghen
  ],
)

#align(center + bottom, text(14pt)[
  Academic year 2025-2026
])

// Blank verso after the title page so the abstract starts on a recto
// (right-hand) page when printed double-sided (recto-verso).
#pagebreak(to: "odd")

// ---------------------------------------------------------------------------
// Abstract
// ---------------------------------------------------------------------------

#v(50pt)
#align(center, text(20pt, weight: "bold")[Abstract])
#v(20pt)

This thesis develops a SAT-based framework for the procedural generation of solvable,
cooperative levels for the Laser Learning Environment (LLE), a multi-agent reinforcement
learning benchmark. We formalise bounded-horizon LLE solvability as a propositional
satisfiability decision problem and prove the reduction correct; we introduce a
strict-beam-semantics counterfactual that turns the *cooperation-required* property into a
second decidable problem on the same level; and we further classify cooperative levels by
the structure of their inter-agent dependencies into five profiles: asymmetric, mutual,
chain, distributed, and fully coupled. These decision
procedures are embedded inside a family of procedural generators (Random, Constrained Random,
Constructive, Level-6-Style) that emit only levels certified by the solver to be solvable
and, on demand, to require cooperation, possibly of a specific profile (one of the five above). The empirical evaluation compares two SAT encodings, characterises per-generator
rejection rates and cooperation-profile distributions, and shows that off-the-shelf
value-based cooperative-MARL algorithms (IQL, VDN, QMIX) can learn certified cooperative levels at
$5 times 5$ and that enlarging the generated training pool restores generalisation. A final set
of curriculum experiments finds that curriculum *scheduling* offers no advantage over direct
training on a reachable target, and that no curriculum — including a staged budget of two million
steps — lets these algorithms solve the mutually-cooperative LLE Level 6, on which direct training
also scores zero; we trace this negative result to the base task being unlearnable by
value-decomposition methods rather than to a failure of curriculum design.

#v(20pt)
*Keywords:* multi-agent reinforcement learning, procedural content generation, SAT solving,
cooperative levels, Laser Learning Environment, curriculum learning.

#pagebreak()


// Table of contents
#outline()

#counter(page).update(0)
#set page(numbering: "1")

= Introduction <introduction>

#include "chapters/introduction.typ"

= Related Work <related-work>

#include "chapters/related_work.typ"

= Background and Formalization <background>

#include "chapters/methods/background.typ"

#include "chapters/methods/formalization.typ"

= SAT-based Solver <sat-reduction>

#include "chapters/contribution/sat_reduction.typ"

= Cooperation Detection <cooperation-detection>

#include "chapters/contribution/cooperation.typ"

= Procedural Generators <generators>

#include "chapters/contribution/generators.typ"

= Empirical Evaluation <experiments>

#include "chapters/contribution/benchmarking.typ"

#include "chapters/experiments.typ"

= Conclusion <conclusion>

#include "chapters/conclusion.typ"

#pagebreak()
#bibliography("bibliography.bib", full: true)

#[
  // The `Appendix` heading inside appendix.typ uses `numbering: none`, so it
  // does NOT advance the depth-1 counter. We therefore reset the counter to 1
  // here, which leaves the Appendix heading sitting at chapter 1; the first
  // depth-2 heading then lands at (1, 1) -> "A.1".
  #counter(heading).update(1)
  #set heading(numbering: (..nums) => {
    let n = nums.pos()
    let letters = ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
                   "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z")
    let letter = letters.at(n.at(0) - 1, default: "?")
    if n.len() == 1 { letter } else { letter + "." + n.slice(1).map(str).join(".") }
  })
  #include "chapters/appendix.typ"
]
