# CAS Offline Compiler Terminal

Portable, dependency-free CAS compiler terminal with the online compiler's
examples, symbol palette, reference panel, syntax colors, terminal diagram
previews, CAS logo treatment, and PWA-style offline SVG/HTML rendering.

It only needs Python 3.10+. It does not need Node, React, Vercel, Railway,
network access, auth, a database, or the dashboard.

## Build The Ship Folder

From the repo root:

```powershell
python offline-cas/build_offline_package.py
```

This creates:

```text
dist/cas-offline/
dist/cas-offline.zip
```

## Run The Offline Terminal

```powershell
cd dist/cas-offline
python cas.py
```

The REPL starts with the CAS banner and supports the same core terminal commands
as the online compiler:

```text
:help
:examples
:natural
:mirror
:dict
:dict noetic
:learn
:example 16
:palette
:ref
:history
:clear
:grammar
:demo
:diagram
:svg my_diagram.svg
:html my_diagram.html
:quit
```

Every valid expression that emits a diagram prints a compact terminal diagram
with PWA-matched symbol colors and writes these files by default:

```text
cas_diagram.svg
cas_diagram.html
```

## One-Shot Examples

```powershell
python cas.py --examples
python cas.py --natural
python cas.py --mirror
python cas.py --dict
python cas.py --dict noetic
python cas.py --learn
python cas.py --example 16 --auto-files
python cas.py "Product(Noetics, Domains)" --svg product.svg --html product.html
python cas.py "NoeticCluster{^2, ^7} subseteq Noetics" --auto-files
python cas.py "Theta(Omega_focus) = 0.6*^1^C + 0.4*^7^O -> Omega_focus"
```

`--html` writes a standalone offline compiler page, not a plain image wrapper:
it includes the dark PWA shell, CAS ASCII logo, 10-dot formation, palette,
reference panel, highlighted expression, result card, layout chips, terminal
preview, and SVG diagram.

Use `--color` to force ANSI colors and `--no-color` to suppress them.

## CAS-Ohm calculations

The compiler accepts named calculations for attention flow (`I=V/R`), required
Drive (`V=IR`), and effective constraint (`R=V/I`). Each input carries its
quantity type, a declared linear scale, its origin, and a source reference.
The scale below is an illustrative design choice, not a canonical calibration
or a measurement of Helm.

```cas
let scale = ohm_scale("illustrative-linear-v1", "drive-units", "attention-units");
let potential = ohm_drive("12", scale, "design", "example:declared-drive");
let constraint = ohm_constraint("4", scale, "design", "example:declared-constraint");
ohm_flow(potential, constraint)
```

This calculates attention flow `3` in the declared attention units. Numeric
values also work (`ohm_drive(12, ...)`); decimal strings preserve exact decimal
input even beyond floating-point precision. The result retains the supplied
provenance and labels the output as calculated. A supplied measurement reference
is a declaration by the caller, not verification that a measurement occurred.

Use `ohm_attention(value, scale, origin, reference)` for a supplied flow, then
`ohm_required_drive(attention, constraint)` or
`ohm_effective_constraint(potential, attention)` for the other two calculations.
Wrong quantity types, mismatched scales, invalid numbers, missing arguments,
and zero denominators produce invalid compiler artifacts. For example:

```cas
let scale = ohm_scale("illustrative-linear-v1", "drive-units", "attention-units");
ohm_flow(ohm_drive("12", scale, "design", "example:drive"), ohm_constraint("0", scale, "design", "example:zero-constraint"))
```

The optional type annotations are `ohm_scale`, `ohm_drive`, `ohm_attention`, and
`ohm_constraint`. Existing CAS symbols keep their meanings; use the named
operations for these calculations. They do not measure Helm, control a live
circuit, or establish correctness of a cognitive result. Both compiler files
must travel together: `api/notation/compiler.py` and `api/notation/cas_ohm.py`.

## Full Demo Pack

Generate SVG and HTML diagrams for every bundled example:

```powershell
python cas.py --demo
```

That writes files under:

```text
examples/
```

## ASCII Aliases

```text
in / notin / subset / subseteq / supset / supseteq / emptyset
Theta / Omega / Lambda / kappa / iota / eta / Phi
```

## Boundary

This is the offline compiler package, not the full web app. It includes compiler
semantics, examples, reference/help surfaces, terminal graphics, and SVG/HTML
diagram rendering. It intentionally excludes the dashboard UI, API server,
natural-language backend endpoint, auth, deployment config, and training stack.
