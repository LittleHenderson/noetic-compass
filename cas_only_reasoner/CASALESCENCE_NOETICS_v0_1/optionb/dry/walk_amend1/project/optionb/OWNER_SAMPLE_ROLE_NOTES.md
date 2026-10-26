# Option B: 20 sample role notes for the owner

**Status: built after seal step 1 and before seal step 2. These notes are not sealed yet.**

Built on 2026-10-05T16:20:00Z by `tools/ob_role_notes.py`. A program built every note. No model wrote one. Nobody edited one.

## What this file is

A role note is the text that model B gets next to a passage, in the group called ROLE.
It says which words of the passage occupy which Noetic.
The notes use nine Noetics, `^1` to `^9`. In this study a Noetic is used as a role that words of the passage can occupy.
Each note prints the definition lines it needs.

The program copies those definition lines, character for character, from Part A of `02_LABELING_GUIDE_v1_2.md`.
The sha256 of that file is `3ed4196dbfb0ad0d96a785f03929229e18d23ff226c7687df363d683bfd8022e`.
Nobody retyped a definition.

A note uses only entries that both label teams agree on.
An entry is one marked role: a Noetic, the quoted words and, where the guide asks for them, the Mind and the related thing.
Team A is Claude Sonnet sub-agents. Team B is DeepSeek `deepseek-chat`.
An entry that only one team gave is left out of the note. It is counted under each note below.

A program drew these 20 passages with seed 20261016 from the 139 eligible passages. Nobody chose them.
The seed is a rule of the plan (PROPOSED). The count of 139 eligible passages is REAL: the program counted it in this run.

## How one note is laid out

1. First come the definition lines. There is one for each Noetic that appears in the note, in number order.
2. Then come the `^1` lines. A `^1` line holds the label only.
3. Then come the other entries, in the order their words appear in the passage.
4. The label is the shorter of the two teams' quotes.
5. The supporting quote is the whole sentence, or sentences, of the passage that hold both teams' quotes.
6. `same as for "..."` means that supporting quote was already printed higher up in the same note.

Model B sees a note under the plain heading `Notes:`, after one padding line. Those two lines are not shown here.

## How long the notes are

REAL, measured in this run on all 139 notes. Words are counted by splitting on white space.

| Text | Shortest | Median | Longest |
|---|---:|---:|---:|
| ROLE | 56 | 134 | 134 |
| MIXED | 54 | 133 | 133 |
| QUOTES-ONLY | 19 | 52 | 52 |
| the passages themselves | 53 | 53 | 53 |

The median is the middle value: half the notes are shorter and half are longer.
ROLE is the tested note. MIXED is the same note with wrong role tags; it is a control.
QUOTES-ONLY is the same labels and supporting quotes with no role tags; it is a control.
Only ROLE notes are shown below.

## What the owner is asked

This file is the sample that question 14 of the plan offers (`08_OPTION_B_PLAN_v1_0.md`, section 22).
It can help with questions 6 and 7 of the same section:

- Question 6. May the canon definition lines be printed, word for word, inside the role notes that model B reads?
- Question 7. Is the stand-in acceptable: label = the shorter quote, supporting quote = the whole sentence?

Until the owner says otherwise, the plan's defaults apply: the lines are printed, and the stand-in is used.
The owner is the only authority on the definitions.

---

## Sample 1 of 20: passage V040

**Passage**

> Fennin opened the nail forge before dawn. He always reached for the tar mould before the wire mould. The bucket stood on the table by the door. A roll of tape lay beside it. He kept well away from the lye vat. Every morning for nine years he had dusted the bucket first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Fennin".
- ^2 Positive: "the tar mould". For the Mind "Fennin". Supporting quote: "He always reached for the tar mould before the wire mould."
- ^3 Negative: "the lye vat". For the Mind "Fennin". Supporting quote: "He kept well away from the lye vat."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Fennin". Relative to "the bucket". Supporting quote: "Every morning for nine years he had dusted the bucket first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 2 of 20: passage V137

**Passage**

> Odrey opened the dye house before dawn. She always reached for the wooden ladle before the metal ladle. The kettle stood on the stove by the door. A coil of rope lay beside it. She kept well away from the leaky bellows. Every morning for nine years she had dusted the kettle first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Odrey".
- ^2 Positive: "the wooden ladle". For the Mind "Odrey". Supporting quote: "She always reached for the wooden ladle before the metal ladle."
- ^3 Negative: "the leaky bellows". For the Mind "Odrey". Supporting quote: "She kept well away from the leaky bellows."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Odrey". Relative to "the kettle". Supporting quote: "Every morning for nine years she had dusted the kettle first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 3 of 20: passage V111

**Passage**

> Coric opened the seed store before dawn. She always reached for the wooden brush before the metal brush. The ledger stood on the shelf by the door. A stack of pallets lay beside it. She kept well away from the loose stair. Every morning for nine years she had dusted the ledger first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Coric".
- ^2 Positive: "the wooden brush". For the Mind "Coric". Supporting quote: "She always reached for the wooden brush before the metal brush."
- ^3 Negative: "the loose stair". For the Mind "Coric". Supporting quote: "She kept well away from the loose stair."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Coric". Relative to "the ledger". Supporting quote: "Every morning for nine years she had dusted the ledger first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 4 of 20: passage V081

**Passage**

> Coret opened the seed store before dawn. She always reached for the oak hammer before the tin hammer. The sledge stood on the shelf by the door. A coil of rope lay beside it. She kept well away from the leaky bellows. Every morning for nine years she had dusted the sledge first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Coret".
- ^2 Positive: "the oak hammer". For the Mind "Coret". Supporting quote: "She always reached for the oak hammer before the tin hammer."
- ^3 Negative: "the leaky bellows". For the Mind "Coret". Supporting quote: "She kept well away from the leaky bellows."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Coret". Relative to "the sledge". Supporting quote: "Every morning for nine years she had dusted the sledge first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 5 of 20: passage V119

**Passage**

> Halic opened the dye house before dawn. She always reached for the bone saw before the steel saw. The kettle stood on the ledge by the door. A stack of pallets lay beside it. She kept well away from the broken ladder. Every morning for nine years she had dusted the kettle first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Halic".
- ^2 Positive: "the bone saw". For the Mind "Halic". Supporting quote: "She always reached for the bone saw before the steel saw."
- ^3 Negative: "the broken ladder". For the Mind "Halic". Supporting quote: "She kept well away from the broken ladder."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Halic". Relative to "the kettle". Supporting quote: "Every morning for nine years she had dusted the kettle first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 6 of 20: passage V050

**Passage**

> Maro opened the net loft before dawn. He always reached for the curved tray before the straight tray. The rack stood on the table by the door. A ball of twine lay beside it. He kept well away from the bilge pump. Every morning for nine years he had dusted the rack first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Maro".
- ^2 Positive: "the curved tray". For the Mind "Maro". Supporting quote: "He always reached for the curved tray before the straight tray."
- ^3 Negative: "the bilge pump". For the Mind "Maro". Supporting quote: "He kept well away from the bilge pump."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Maro". Relative to "the rack". Supporting quote: "Every morning for nine years he had dusted the rack first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 7 of 20: passage V030

**Passage**

> Sunnen opened the bell tower before dawn. He always reached for the copper ruler before the iron ruler. The ledger stood on the table by the door. A heap of straw lay beside it. He kept well away from the rusty winch. Every morning for nine years he had dusted the ledger first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Sunnen".
- ^2 Positive: "the copper ruler". For the Mind "Sunnen". Supporting quote: "He always reached for the copper ruler before the iron ruler."
- ^3 Negative: "the rusty winch". For the Mind "Sunnen". Supporting quote: "He kept well away from the rusty winch."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Sunnen". Relative to "the ledger". Supporting quote: "Every morning for nine years he had dusted the ledger first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 8 of 20: passage V140

**Passage**

> Marey opened the net loft before dawn. He always reached for the small ruler before the large ruler. The rack stood on the table by the door. A pair of tongs lay beside it. He kept well away from the broken ladder. Every morning for nine years he had dusted the rack first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Marey".
- ^2 Positive: "the small ruler". For the Mind "Marey". Supporting quote: "He always reached for the small ruler before the large ruler."
- ^3 Negative: "the broken ladder". For the Mind "Marey". Supporting quote: "He kept well away from the broken ladder."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Marey". Relative to "the rack". Supporting quote: "Every morning for nine years he had dusted the rack first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 9 of 20: passage V065

**Passage**

> Maris opened the dye house before dawn. She always reached for the birch spindle before the zinc spindle. The kettle stood on the table by the door. A coil of rope lay beside it. She kept well away from the rusty winch. Every morning for nine years she had dusted the kettle first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Maris".
- ^2 Positive: "the birch spindle". For the Mind "Maris". Supporting quote: "She always reached for the birch spindle before the zinc spindle."
- ^3 Negative: "the rusty winch". For the Mind "Maris". Supporting quote: "She kept well away from the rusty winch."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Maris". Relative to "the kettle". Supporting quote: "Every morning for nine years she had dusted the kettle first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 10 of 20: passage V141

**Passage**

> Corey opened the seed store before dawn. She always reached for the curved saw before the straight saw. The oilcan stood on the shelf by the door. A tub of madder lay beside it. She kept well away from the bilge pump. Every morning for nine years she had dusted the oilcan first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Corey".
- ^2 Positive: "the curved saw". For the Mind "Corey". Supporting quote: "She always reached for the curved saw before the straight saw."
- ^3 Negative: "the bilge pump". For the Mind "Corey". Supporting quote: "She kept well away from the bilge pump."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Corey". Relative to "the oilcan". Supporting quote: "Every morning for nine years she had dusted the oilcan first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 11 of 20: passage V074

**Passage**

> Halis opened the net loft before dawn. He always reached for the long ruler before the short ruler. The kettle stood on the ledge by the door. A ball of twine lay beside it. He kept well away from the leaky bellows. Every morning for nine years he had dusted the kettle first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Halis".
- ^2 Positive: "the long ruler". For the Mind "Halis". Supporting quote: "He always reached for the long ruler before the short ruler."
- ^3 Negative: "the leaky bellows". For the Mind "Halis". Supporting quote: "He kept well away from the leaky bellows."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Halis". Relative to "the kettle". Supporting quote: "Every morning for nine years he had dusted the kettle first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 12 of 20: passage V016

**Passage**

> Tamen opened the nail forge before dawn. He always reached for the oak ladle before the tin ladle. The stool stood on the shelf by the door. A roll of tape lay beside it. He kept well away from the rusty winch. Every morning for nine years he had dusted the stool first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Tamen".
- ^2 Positive: "the oak ladle". For the Mind "Tamen". Supporting quote: "He always reached for the oak ladle before the tin ladle."
- ^3 Negative: "the rusty winch". For the Mind "Tamen". Supporting quote: "He kept well away from the rusty winch."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Tamen". Relative to "the stool". Supporting quote: "Every morning for nine years he had dusted the stool first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 13 of 20: passage V048

**Passage**

> Ilso opened the bell tower before dawn. He always reached for the long hammer before the short hammer. The ledger stood on the counter by the door. A roll of tape lay beside it. He kept well away from the loose stair. Every morning for nine years he had dusted the ledger first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Ilso".
- ^2 Positive: "the long hammer". For the Mind "Ilso". Supporting quote: "He always reached for the long hammer before the short hammer."
- ^3 Negative: "the loose stair". For the Mind "Ilso". Supporting quote: "He kept well away from the loose stair."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Ilso". Relative to "the ledger". Supporting quote: "Every morning for nine years he had dusted the ledger first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 14 of 20: passage V018

**Passage**

> Ilsen opened the bell tower before dawn. He always reached for the hemp mould before the nylon mould. The sledge stood on the counter by the door. A ball of twine lay beside it. He kept well away from the leaky bellows. Every morning for nine years he had dusted the sledge first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Ilsen".
- ^2 Positive: "the hemp mould". For the Mind "Ilsen". Supporting quote: "He always reached for the hemp mould before the nylon mould."
- ^3 Negative: "the leaky bellows". For the Mind "Ilsen". Supporting quote: "He kept well away from the leaky bellows."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Ilsen". Relative to "the sledge". Supporting quote: "Every morning for nine years he had dusted the sledge first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 15 of 20: passage V001

**Passage**

> Tama opened the boat shed before dawn. She always reached for the tar brush before the wire brush. The lantern stood on the shelf by the door. A coil of rope lay beside it. She kept well away from the bilge pump. Every morning for nine years she had dusted the lantern first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Tama".
- ^2 Positive: "the tar brush". For the Mind "Tama". Supporting quote: "She always reached for the tar brush before the wire brush."
- ^3 Negative: "the bilge pump". For the Mind "Tama". Supporting quote: "She kept well away from the bilge pump."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Tama". Relative to "the lantern". Supporting quote: "Every morning for nine years she had dusted the lantern first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 16 of 20: passage V126

**Passage**

> Corar opened the bell tower before dawn. He always reached for the long ladle before the short ladle. The sledge stood on the shelf by the door. A heap of straw lay beside it. He kept well away from the broken ladder. Every morning for nine years he had dusted the sledge first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Corar".
- ^2 Positive: "the long ladle". For the Mind "Corar". Supporting quote: "He always reached for the long ladle before the short ladle."
- ^3 Negative: "the broken ladder". For the Mind "Corar". Supporting quote: "He kept well away from the broken ladder."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Corar". Relative to "the sledge". Supporting quote: "Every morning for nine years he had dusted the sledge first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 17 of 20: passage V097

**Passage**

> Eddol opened the boat shed before dawn. She always reached for the wicker saw before the mesh saw. The stool stood on the stove by the door. A coil of rope lay beside it. She kept well away from the loose stair. Every morning for nine years she had dusted the stool first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Eddol".
- ^2 Positive: "the wicker saw". For the Mind "Eddol". Supporting quote: "She always reached for the wicker saw before the mesh saw."
- ^3 Negative: "the loose stair". For the Mind "Eddol". Supporting quote: "She kept well away from the loose stair."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Eddol". Relative to "the stool". Supporting quote: "Every morning for nine years she had dusted the stool first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 18 of 20: passage V110

**Passage**

> Maric opened the net loft before dawn. He always reached for the wicker rake before the mesh rake. The kettle stood on the table by the door. A heap of straw lay beside it. He kept well away from the lye vat. Every morning for nine years he had dusted the kettle first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Maric".
- ^2 Positive: "the wicker rake". For the Mind "Maric". Supporting quote: "He always reached for the wicker rake before the mesh rake."
- ^3 Negative: "the lye vat". For the Mind "Maric". Supporting quote: "He kept well away from the lye vat."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Maric". Relative to "the kettle". Supporting quote: "Every morning for nine years he had dusted the kettle first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 19 of 20: passage V098

**Passage**

> Jossol opened the net loft before dawn. He always reached for the wooden spindle before the metal spindle. The globe stood on the counter by the door. A ball of twine lay beside it. He kept well away from the broken ladder. Every morning for nine years he had dusted the globe first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Jossol".
- ^2 Positive: "the wooden spindle". For the Mind "Jossol". Supporting quote: "He always reached for the wooden spindle before the metal spindle."
- ^3 Negative: "the broken ladder". For the Mind "Jossol". Supporting quote: "He kept well away from the broken ladder."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Jossol". Relative to "the globe". Supporting quote: "Every morning for nine years he had dusted the globe first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 20 of 20: passage V106

**Passage**

> Tamic opened the nail forge before dawn. He always reached for the bone mould before the steel mould. The stool stood on the shelf by the door. A ball of twine lay beside it. He kept well away from the bilge pump. Every morning for nine years he had dusted the stool first.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
^3 Negative — An Idea the Mind is adverse to and repelled by.
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- ^1 Mind: "Tamic".
- ^2 Positive: "the bone mould". For the Mind "Tamic". Supporting quote: "He always reached for the bone mould before the steel mould."
- ^3 Negative: "the bilge pump". For the Mind "Tamic". Supporting quote: "He kept well away from the bilge pump."
- ^7 Rhythm: "Every morning for nine years". For the Mind "Tamic". Relative to "the stool". Supporting quote: "Every morning for nine years he had dusted the stool first."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.
