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

// Alternative title without curriculum learning, in case the transfer
// experiments do not produce conclusive results:
//
//   Procedural Generation of Solvable Cooperative Levels
//   for the Laser Learning Environment
#align(center, text(18pt)[
  *Procedural Generation of Solvable Cooperative Levels \
  for Curriculum Learning in the Laser Learning Environment*
])

#v(10pt)

#grid(
  columns: (1fr, 1fr),
  align(center)[
    *Author:* \
    Charels Hugo \
    #link("mailto:hugo.charels@ulb.be")
  ],
  align(center)[
    *Supervisors:* \
    Lenaerts Tom \
    Molinghen Yannick
  ],
)

#align(center + bottom, text(14pt)[
  Academic year 2025-2026
])

#pagebreak()

// Intentional blank page after the cover.
#v(1fr)
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

#[
  // The `Appendix` heading inside appendix.typ uses `numbering: none`, so it
  // does NOT advance the depth-1 counter. We therefore reset the counter to 1
  // here, which leaves the Appendix heading sitting at chapter 1; the first
  // depth-2 heading then lands at (1, 1) -> "A.1".
  #counter(heading).update(1)
  #set heading(numbering: (..nums) => {
    let n = nums.pos()
    let letters = ("A", "B", "C", "D", "E", "F", "G", "H")
    let letter = letters.at(n.at(0) - 1, default: "?")
    if n.len() == 1 { letter } else { letter + "." + n.slice(1).map(str).join(".") }
  })
  #include "chapters/appendix.typ"
]

#pagebreak()
#bibliography("bibliography.bib", full: true)
