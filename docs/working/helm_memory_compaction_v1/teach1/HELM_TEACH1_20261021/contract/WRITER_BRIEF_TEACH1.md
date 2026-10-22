# WRITER BRIEF — TEACH-1 teaching turns (for the AI model writers; the custodian hands it over with one writer packet)

**Plainly.** You are writing what one person types to a chat assistant while telling it about a small made-up subject:
a family's hive yards over a year, or a small town's bus lines. You write the person's lines only, never the
assistant's. The facts are given to you; you choose the words. Your lines will be typed into the assistant one by one,
exactly as you write them. Nobody will correct them.

Status of this brief: part of the sealed TEACH-1 package (pre-code `7eef0edc…`, amendment A-TEACH1-1). Written before
any exam turn exists. No turn is generated until the owner has typed the line and the custodian has drawn the worlds.
**No paid API call is made without its own owner line.** Free tiers, or model sessions the owner already pays for, only.

## What you receive

One **writer packet** per world (`WRITER_PACKETS_TEACH1.json`, one entry): 32 numbered **slots** in order. Each slot has
a `kind`, and for keyed kinds a `canonical` sentence, a `value`, and `anchor_words`.

| kind | what the line must do | count per world |
|---|---|---|
| `FACT` | state the canonical fact, in your own words, with the given value | 20 |
| `UNKNOWN` | say the person does not remember that fact (state no value for it) | 4 |
| `FIX` | correct an earlier fact: the new value, and that the old value (`not_value`) was wrong | 2 |
| `RESTATE` | say an earlier fact again, the same value, naturally ("as I said…") | 2 |
| `SMALL` | small talk with no fact in it (a pause, a thanks, a remark) | 4 |

## The rules (the custodian's program checks every one; a turn that breaks one comes back to you to rewrite)

1. **One line per slot, in the given order.** Write exactly 32 lines. Keep the slot's `turn_index`.
2. **Carry the anchor words.** Every `FACT`, `UNKNOWN`, `FIX` and `RESTATE` line must contain every word in its
   `anchor_words`, spelled the same (any case, any order, anywhere in the line). They are the words a later question
   will use. Everything else is yours: word order, extra words, tone.
3. **The value, and only the value.** A `FACT`, `FIX` or `RESTATE` line states its `value` (a number as a word, such as
   "twelve", or a name) and no other value of the same kind. A `FIX` line may also name its `not_value`, as the wrong
   one ("not seven"). An `UNKNOWN` line states no value at all for that fact.
4. **Short, as people type.** One or two sentences. At most 60 words (the checker refuses more). About 8 to 25 words is
   typical.
5. **Statements, not questions.** A keyed line never ends with a question mark and never asks the assistant anything.
6. **Words the assistant treats as something else.** The assistant routes some phrases to other jobs. Never use: talk
   about yourself or your family ("my father", "I live in", "I like", "I love", "I used to", "I'm a"); feelings ("I feel",
   "I'm tired", strong mood words such as "awful", "wonderful", "love", "hate"); asking what it remembers or knows ("what
   did I say", "remember what I said", "what do you know"); kitchen or food words (recipe, ingredient, flour, water,
   sugar, butter, egg, milk, salt, yeast, bread, cups, pantry, stock, inventory, "how much", "how many" outside an
   `UNKNOWN` line); computer words (write, create, test, run, git, code, design, cloud); "study", "explore", "learn
   about"; jokes. The custodian also types every line into the assistant once, in a throwaway session, and refuses any
   line it routes anywhere but its plain-conversation branch.
7. **No outside facts.** Use only names from your packet. Do not add a place, a person, a number or a month that is not
   in your packet.
8. **No copying.** Do not reuse the canonical sentence word for word; at least one change of wording per keyed line.
   (The split check refuses any 8-word run shared with the generator's templates or with a spent exam.)
9. **Rewrites.** If a line is refused, you get the slot and the reason back and write it again. Nothing else changes.

## What you return

A JSON list of 32 objects, one per slot: `{"turn_index": <int>, "text": "<your line>"}`. The custodian adds your
writer label (`LLM_WRITTEN`, vendor, model name, version) and passes the file to two keyers of two other model families
(contract/KEY_FORMAT_TEACH1.md).

## Two examples (made up for this brief; never in any exam)

- Slot `FACT`, canonical "The Ashby yard had eleven colonies in March.", anchor words `colonies, ashby, yard, march`:
  "Back in March the Ashby yard was up to eleven colonies, which surprised everyone." (accepted)
- The same slot: "Ashby was doing well in March." (refused: anchor words `colonies`, `yard` missing; value missing)
