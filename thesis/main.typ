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

    if { 0 < chapter_num and chapter_num < 6 } {
      pagebreak()
      v(100pt)

      let chapter = text(strong("Chapter " + str(chapter_num)), 22pt)
      let content = text(strong(it.body), 30pt)
      chapter + [ \ \ ] + content + [ \ \ ]
    } else {
      if it.body == [Conclusion] {
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

= Background

#include "chapters/background.typ"

= Related Work

#include "chapters/related_work.typ"

= Methods

#include "chapters/methods/formalization.typ"

== Solver by Reduction to SAT <sat-reduction>

#include "chapters/sat_reduction.typ"

#include "chapters/methods/cooperation.typ"

#include "chapters/methods/generators.typ"

#include "chapters/methods/benchmarking.typ"

= Experiments <experiments>

#include "chapters/experiments.typ"

= Conclusion

#include "chapters/conclusion.typ"

#pagebreak()
#bibliography("bibliography.bib", full: true)
