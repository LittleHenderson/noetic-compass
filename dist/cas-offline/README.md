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
