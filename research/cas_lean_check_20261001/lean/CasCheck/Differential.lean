import CasCheck.Core
import CasCheck.Bounded
import CasCheck.Generated
/-!
# Is the Lean copy faithful? Lean against the real compiler

`export_compiler_facts.py` runs real CAS source text through the real `compile_expression` and
writes every answer into `Generated.lean` (and, for 5-term words, `nest5.txt`). This file reads
those answers and compares each one with the Lean copy of the rules.

Record kinds (one per line, numbers separated by spaces):
* `C a b times circ compose divide`: `^a^C * ^b^C`, `^a^C ∘ ^b^C`, `compose(^a^C, ^b^C)`, `^a^C / ^b^C`
  (the result's Noetic; 99 = did not compile). All 100 pairs.
* `A s t valid admissible descent`: `->` between states s and t. All 1,600 pairs.
* `D l r res` / `Q l r res`: the Domain of `^1^X * ^1^Y` / `^1^X / ^1^Y` (9 = refused). All 16 pairs each.
* `P a b dom`: the dominant state of `^a^C + ^b^C`. All 100 pairs.
* `M i dom keys`: `x - x` for every one of the 40 states.
* `S code value`: set facts (`|Noetics|` ... `PartitionOf(...)`).
* `L code noetic domain drive label`: how the compiler itself reads each alphabet letter.
* `N ...`: one nested word (see `parseN`).
-/
namespace Cas.Diff
open Cas Cas.Nesting

def toks (line : String) : List String := (line.splitOn " ").filter (· ≠ "")
def records (s : String) : List (List String) := ((s.splitOn "\n").map toks).filter (· ≠ [])
def nums (l : List String) : List Nat := l.map String.toNat!

def optCode : Option Nat → Nat
  | some d => d
  | none => 9

def checkC : List Nat → Bool
  | [a, b, times, circ, comp, dv] =>
    times == compose a b && circ == compose a b && comp == compose a b && dv == divide a b
  | _ => false

def checkA : List Nat → Bool
  | [s, t, valid, adm, desc] =>
    if arrowCompiles s t then
      valid == 1 && ((adm == 1) == (arrow s t).1) && ((desc == 1) == (arrow s t).2)
    else valid == 0
  | _ => false

def checkD : List Nat → Bool
  | [l, r, res] => res == optCode (timesDomain l r)
  | _ => false

def checkQ : List Nat → Bool
  | [l, r, res] => res == optCode (divideDomain l r)
  | _ => false

def checkP : List Nat → Bool
  | [a, b, dom] => some dom == dominant (plus (lit (10 + a)) (lit (10 + b)))
  | _ => false

def checkM : List Nat → Bool
  | [i, dom, keys] => minus (lit i) (lit i) == lit i && dom == i && keys == 1
  | _ => false

/-- Expected set facts: |Noetics| = 10, |Domains| = 4, |Drives| = 7, |Registers| = 4, |States| = 40,
|SubFoundations| = 28, |Foundations| = 7, |Product(Noetics, Domains)| = 40,
`PartitionOf(SubFoundations, Foundation_1..7)` compiles (1), |Product(Drives, Registers)| = 28. -/
def expectedSets : List Nat := [10, 4, 7, 4, 40, 28, 7, 40, 1, 28]

def checkS : List Nat → Bool
  | [code, value] => expectedSets.getD code 999 == value
  | _ => false

def letter (c : Nat) : Term := alphabet.getD c default

def checkL : List Nat → Bool
  | [code, n, d, dr, lab] => letter code == ⟨n, d, dr, lab⟩ && code < alphabet.length
  | _ => false

/-! ## Nested words -/

def takeN (n : Nat) (l : List Nat) : Option (List Nat × List Nat) :=
  if l.length ≥ n then some (l.take n, l.drop n) else none

def readCount : List Nat → Option (List Nat × List Nat)
  | n :: rest => takeN n rest
  | [] => none

def pairsOf : List Nat → List (Nat × Nat)
  | a :: b :: r => (a, b) :: pairsOf r
  | _ => []

def readCrit (l : List Nat) : Option ((List (Nat × Nat) × List Nat) × List Nat) := do
  let (ps, l) ← (match l with
    | n :: rest => takeN (2 * n) rest
    | [] => none)
  let (us, l) ← readCount l
  pure ((pairsOf ps, us), l)

structure NRec where
  word : List Nat
  so : List Nat
  eo : List Nat
  crit : List (List (Nat × Nat) × List Nat)
  mets : List Nat

/-- `N k c1..ck  n s1..sn  n e1..en  [n p q .. m u1..um] x3  met_base met_either met_any`:
the letters; the surviving positions in the surfacing-first and the either-order canonical form;
(resolved pairs, unresolved positions) for the base, either-order and any-landing readings;
`met` for each (0 false, 1 true, 2 None). -/
def parseN (l : List Nat) : Option NRec := do
  let (w, l) ← readCount l
  let (so, l) ← readCount l
  let (eo, l) ← readCount l
  let (c1, l) ← readCrit l
  let (c2, l) ← readCrit l
  let (c3, l) ← readCrit l
  let (m, _) ← takeN 3 l
  pure { word := w, so := so, eo := eo, crit := [c1, c2, c3], mets := m }

def survivors (eo : Bool) (w : List Term) : List Nat :=
  (reduce (·.2) eo ((List.range w.length).zip w)).map (·.1)

def metCode : Option Bool → Nat
  | some false => 0
  | some true => 1
  | none => 2

def checkN (l : List Nat) : Bool :=
  match parseN l with
  | none => false
  | some r =>
    let w := r.word.map letter
    survivors false w == r.so && survivors true w == r.eo &&
    r.crit == [criterion false false w, criterion true false w, criterion false true w] &&
    r.mets == [metCode (met false false w), metCode (met true false w), metCode (met false true w)]

def checkRecord : List String → Bool
  | tag :: rest =>
    let n := nums rest
    match tag with
    | "C" => checkC n
    | "A" => checkA n
    | "D" => checkD n
    | "Q" => checkQ n
    | "P" => checkP n
    | "M" => checkM n
    | "S" => checkS n
    | "L" => checkL n
    | "N" => checkN n
    | _ => false
  | [] => false

def countTag (rs : List (List String)) (tag : String) : Nat :=
  (rs.filter (fun r => r.head? == some tag)).length

/-- How many records of each kind the comparison must see, so that "all agree" cannot be vacuous. -/
def expectedCounts : List (String × Nat) :=
  [("C", 100), ("A", 1600), ("D", 16), ("Q", 16), ("P", 100), ("M", 40), ("S", 10), ("L", 9)]

def coreRecords : List (List String) := records Generated.coreData
def nestRecords : List (List String) := records Generated.nestData

def coreOk : Bool :=
  coreRecords.all checkRecord && expectedCounts.all (fun (t, c) => countTag coreRecords t == c)

/-- Every word of 2..4 letters over the 9-letter alphabet: 81 + 729 + 6561. -/
def nestOk : Bool :=
  nestRecords.all checkRecord && countTag nestRecords "N" == 7371

end Cas.Diff
