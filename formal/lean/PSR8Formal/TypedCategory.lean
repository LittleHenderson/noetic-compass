/-!
# Typed finite-function core

The carrier types enforce sources and targets.  These theorems establish the
category laws for the reference arrow type without any cardinality coercion.
-/

set_option autoImplicit false
set_option warningAsError true

namespace PSR8

universe u v w x

/-- A typed arrow is a total function with source and target in its type. -/
def Arrow (α : Type u) (β : Type v) := α → β

namespace Arrow

/-- Identity at one exact carrier type. -/
def id {α : Type u} : Arrow α α := fun value => value

/-- Typed composition.  An ill-matched middle type is not an inhabitant. -/
def comp {α : Type u} {β : Type v} {γ : Type w}
    (after : Arrow β γ) (before : Arrow α β) : Arrow α γ :=
  fun value => after (before value)

theorem comp_apply {α : Type u} {β : Type v} {γ : Type w}
    (after : Arrow β γ) (before : Arrow α β) (value : α) :
    comp after before value = after (before value) := rfl

theorem left_identity {α : Type u} {β : Type v} (f : Arrow α β) :
    comp id f = f := rfl

theorem right_identity {α : Type u} {β : Type v} (f : Arrow α β) :
    comp f id = f := rfl

theorem associativity {α : Type u} {β : Type v} {γ : Type w} {δ : Type x}
    (h : Arrow γ δ) (g : Arrow β γ) (f : Arrow α β) :
    comp h (comp g f) = comp (comp h g) f := rfl

/-- Powers are defined only after the source and target have unified. -/
def power {α : Type u} (f : Arrow α α) : Nat → Arrow α α
  | 0 => id
  | n + 1 => comp f (power f n)

theorem power_zero {α : Type u} (f : Arrow α α) : power f 0 = id := rfl

theorem power_succ {α : Type u} (f : Arrow α α) (n : Nat) :
    power f (n + 1) = comp f (power f n) := rfl

end Arrow
end PSR8
