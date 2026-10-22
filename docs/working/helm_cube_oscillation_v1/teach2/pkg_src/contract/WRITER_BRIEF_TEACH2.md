# WRITER BRIEF — TEACH-2 teaching turns (for the AI model writers; the custodian hands it over with one writer packet)

**Plainly.** You are writing what one person types to a chat assistant while telling it about a small made-up subject:
a family's hive yards over a year, or a small town's bus lines. You write the person's lines only, never the
assistant's. The facts are given to you; you choose the words. Your lines will be typed into the assistant one by one,
exactly as you write them. Nobody will correct them.

Status of this brief: part of the sealed TEACH-2 package (pre-code `f7b6183b…`, amendments A-TEACH2-1 to -19; TEACH-1's
brief with the TRAP kind added). Written before any exam turn exists. No turn is generated until the custodian has drawn
the worlds. The owner writes nothing and reviews only (A-TEACH2-17). **No paid API call is made without its own
recorded approval.** Free tiers, or model sessions the owner already pays for, only.

## What you receive

One **writer packet** per world (`WRITER_PACKETS_TEACH2.json`, one entry): 32 numbered **slots** in order. Each slot has
a `kind`, and for keyed kinds a `canonical` sentence, a `value`, and `anchor_words`.

| kind | what the line must do | count per world |
|---|---|---|
| `FACT` | state the canonical fact, in your own words, with the given value | 18 |
| `TRAP` | state the canonical fact with its value AND keep the slot's one decoy (`trap`: an odd "not" that does not deny the fact, a second number such as "up from four the month before", or another yard or line in another month) | 4 |
| `UNKNOWN` | say the person does not remember that fact (state no value for it) | 4 |
| `FIX` | correct an earlier fact: the new value, and that the old value (`not_value`) was wrong | 2 |
| `RESTATE` | say an earlier fact again, the same value, naturally ("as I said…") | 2 |
| `SMALL` | small talk with no fact in it (a pause, a thanks, a remark) | 2 |

A `TRAP` slot with `trap_role` = `FIRST` is that fact's first statement; with `RESTATE` it says an earlier fact again.

## The rules (the custodian's program checks every one; a turn that breaks one comes back to you to rewrite)

1. **One line per slot, in the given order.** Write exactly 32 lines. Keep the slot's `turn_index`.
2. **Carry the anchor words.** Every `FACT`, `TRAP`, `UNKNOWN`, `FIX` and `RESTATE` line must contain every word in its
   `anchor_words`, spelled the same (any case, any order, anywhere in the line).
3. **The value, and only the value.** A `FACT`, `FIX` or `RESTATE` line states its `value` (a number as a word, such as
   "twelve", or a name) and no other value of the same kind. A `FIX` line may also name its `not_value`, as the wrong
   one ("not seven"). An `UNKNOWN` line states no value at all for that fact. A `TRAP` line states its `value` as the
   fact, and the decoy only in the role the slot's `trap` gives it (never as the fact's value).
4. **Short, as people type.** One or two sentences. At most 60 words. About 8 to 25 words is typical.
5. **Statements, not questions.** A keyed line never ends with a question mark and never asks the assistant anything.
6. **Words the assistant treats as something else.** Never use: talk about yourself or your family ("my father", "I
   live in", "I like", "I love", "I used to", "I'm a"); feelings ("I feel", "I'm tired", strong mood words); asking what
   it remembers or knows ("what did I say", "remember what I said", "what do you know"); kitchen or food words (recipe,
   ingredient, flour, water, sugar, butter, egg, milk, salt, yeast, bread, cups, pantry, stock, inventory, "how much",
   "how many" outside an `UNKNOWN` line); computer words (write, create, test, run, git, code, design, cloud); "study",
   "explore", "learn about"; jokes. The custodian types every line into the assistant once, in a throwaway session,
   and refuses any line it routes anywhere but its plain-conversation branch.
7. **No outside facts.** Use only names from your packet. Do not add a place, a person, a number or a month that is not
   in your packet.
8. **No copying.** Do not reuse the canonical sentence word for word; at least one change of wording per keyed line.
   (The split check refuses any 8-word run shared with the generator's templates, the canonical TRAP lines or a spent
   exam.)
9. **Rewrites.** If a line is refused, you get the slot and the reason back and write it again. Nothing else changes.

## What you return

A JSON list of 32 objects, one per slot: `{"turn_index": <int>, "text": "<your line>"}`. The custodian adds your
writer label (`LLM_WRITTEN`, vendor, model name, version) and passes the file to two keyers of two other model families
(contract/KEY_FORMAT_TEACH2.md).

## Examples (made up for this brief; never in any exam)

- Slot `FACT`, canonical "The Ashby yard had eleven colonies in March.", anchor words `colonies, ashby, yard, march`:
  "Back in March the Ashby yard was up to eleven colonies, which surprised everyone." (accepted)
- Slot `TRAP`, canonical "The Ashby yard had eleven colonies in March, up from four the month before.", value
  `eleven`: "In March the Ashby yard reached eleven colonies; a month earlier it had only four." (accepted: the decoy
  "four" stays the earlier month's number, never the March count)
- Slot `FACT`: "Ashby was doing well in March." (refused: anchor words `colonies`, `yard` missing; value missing)
