import CasCheck.Differential
/-!
`lake exe cascheck [nest5.txt]` prints the comparison report: for each record kind, how many records
the real compiler produced, how many agree with the Lean copy, and the first disagreements.
It also counts FINDING N-A over the bounded word set. It never decides a claim on its own;
the theorems in `DiffTheorems.lean`, `Laws.lean`, `Nesting.lean` and `Bounded.lean` do.
-/
open Cas Cas.Diff Cas.Nesting

def report (title : String) (rs : List (List String)) : IO Bool := do
  let tags := (rs.filterMap List.head?).eraseDups
  let mut allOk := true
  IO.println s!"== {title}: {rs.length} records"
  for t in tags do
    let mine := rs.filter (fun r => r.head? == some t)
    let bad := mine.filter (fun r => !checkRecord r)
    IO.println s!"   {t}: {mine.length} records, {mine.length - bad.length} agree, {bad.length} disagree"
    for r in bad.take 5 do
      IO.println s!"      DISAGREE: {" ".intercalate r}"
    if !bad.isEmpty then allOk := false
  return allOk

def termText (t : Term) : String :=
  let d := ["P", "C", "E", "O"].getD t.domain ""
  let dom := if d == "" then "" else s!"^{d}"
  let drv := if t.drive == 0 then "" else s!"_\{F{t.drive}}"
  let reg := ["", "|T", "|A", "|f", "|E"].getD t.label "|?"
  s!"^{t.noetic}{dom}{drv}{reg}"

def wordText (w : List Term) : String := " ∘ ".intercalate (w.map termText)

def main (args : List String) : IO UInt32 := do
  IO.println s!"compiler blob: {Generated.compilerBlob}"
  IO.println s!"compiler engine: {Generated.engine}"
  let ok1 ← report "core rules" coreRecords
  for (t, c) in expectedCounts do
    if countTag coreRecords t != c then
      IO.println s!"   COUNT WRONG: {t} has {countTag coreRecords t}, expected {c}"
  let ok2 ← report "nested words, 2-4 terms" nestRecords
  -- Extra answer files: `core:PATH` (core records) or a plain PATH / `nest:PATH` (nested words).
  let mut ok3 := true
  for arg in args do
    if arg.startsWith "core:" then
      let path := arg.drop 5
      let rs := records (← IO.FS.readFile path)
      let ok ← report s!"core rules from {path}" rs
      for (t, c) in expectedCounts do
        if countTag rs t != c then
          IO.println s!"   COUNT WRONG: {t} has {countTag rs t}, expected {c}"
      ok3 := ok3 && ok
    else
      let path := if arg.startsWith "nest:" then arg.drop 5 else arg
      let ok ← report s!"nested words from {path}" (records (← IO.FS.readFile path))
      ok3 := ok3 && ok
  let amb := eitherOrderAmbiguous
  IO.println s!"== FINDING N-A: {amb.length} of {W5.length} words (1-5 terms) have two or more either-order canonical forms"
  for w in amb.take 5 do
    let forms := (normalForms true w.length (live id w)).map wordText
    IO.println s!"   {wordText w}  ->  {forms}   (compiler reports: {wordText (reduce id true w)})"
  let verdict := ok1 && ok2 && ok3 && coreOk && nestOk
  IO.println s!"== RESULT: {if verdict then "LEAN COPY AGREES WITH THE COMPILER ON EVERY RECORD" else "DISAGREEMENTS FOUND"}"
  return (if verdict then 0 else 1)
