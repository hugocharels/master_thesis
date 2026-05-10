// Document settings

#set page(
  number-align: center,
)
#set heading(
  numbering: "1.1",
)

#set text(lang: "en")

#show heading: it => {
  if it.depth == 1 {
    let chapter_num = counter(heading.where(level: 1)).at(it.location()).at(0)

    if { 0 < chapter_num and chapter_num < 5 } {
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

#align(center, text(18pt)[
  *Procedural Generation of Solvable Cooperative Levels for the \
  Laser Learning Environment*
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

// Table of contents
#outline()

#counter(page).update(0)
#set page(numbering: "1")

= Introduction

#include "chapters/introduction.typ"

= State of the Art

#include "chapters/related_work.typ"

= Method

#include "chapters/methods/background.typ"

#include "chapters/methods/formalization.typ"

= Experiments

== Part 1 — Contribution

#include "chapters/contribution/overview.typ"

#[
  #set heading(offset: 1)
  == Solver by Reduction to SAT <sat-reduction>
  #include "chapters/contribution/sat_reduction.typ"
  #include "chapters/contribution/benchmarking.typ"
  #include "chapters/contribution/cooperation.typ"
  #include "chapters/contribution/generators.typ"
]

== Part 2 — Results <experiments>

#[
  #set heading(offset: 1)
  #include "chapters/experiments.typ"
]

= Conclusion

#include "chapters/conclusion.typ"

#[
  #set heading(numbering: (..nums) => {
    let n = nums.pos()
    let letters = ("A", "B", "C", "D", "E", "F", "G", "H")
    let letter = letters.at(n.at(0) - 5, default: "?")
    if n.len() == 1 { letter }
    else { letter + "." + n.slice(1).map(str).join(".") }
  })
  #include "chapters/appendix.typ"
]

#pagebreak()
#bibliography("bibliography.bib", full: true)
