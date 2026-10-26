# Option B: 20 sample role notes for the owner

**Status: built after seal step 1 and before seal step 2. These notes are not sealed yet.**

Built on 2026-10-07T02:25:59Z by `tools/ob_role_notes.py`. A program built every note. No model wrote one. Nobody edited one.

## What this file is

A role note is the text that model B gets next to a passage, in the group called ROLE.
It says which words of the passage occupy which Noetic.
The notes use nine Noetics, `^1` to `^9`. In this study a Noetic is used as a role that words of the passage can occupy.
Each note prints the definition lines it needs.
Right after each definition line it prints one line with that Noetic's canonical sayings. That line starts with the word `Sayings`.

The program copies those definition lines, character for character, from Part A of `02_LABELING_GUIDE_v1_2.md`.
The sha256 of that file is `3ed4196dbfb0ad0d96a785f03929229e18d23ff226c7687df363d683bfd8022e`.
Nobody retyped a definition.

The program copies the sayings, character for character, from the table "Canonical colloquialism map" in Clarification 6 of `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`.
The sha256 of that file is `cda85c03273c47f7df9ac53258920b95ba7b3b2007b0e760856a67497f661880`.
Nobody retyped a saying. The program builds no note if a definition in that table differs from the guide.

**The sayings lines are new (amendment A13).**
They are the operator's reading of the owner's ruling of 2026-10-05 on the colloquialisms.
That ruling is about labeling. It does not name these notes. So the owner may strike the sayings lines (question 22 below).
The owner's sentence about Mind is not printed in any note.
The labels behind these notes were made under labeling guide version 1.2, before that ruling. They were not made again.

A note uses only entries that both label teams agree on.
An entry is one marked role: a Noetic, the quoted words and, where the guide asks for them, the Mind and the related thing.
Team A is Claude Sonnet sub-agents. Team B is DeepSeek `deepseek-chat`.
An entry that only one team gave is left out of the note. It is counted under each note below.

A program drew these 20 passages with seed 20261016 from the 192 eligible passages. Nobody chose them.
The seed is a rule of the plan (PROPOSED). The count of 192 eligible passages is REAL: the program counted it in this run.

## How one note is laid out

1. First comes the head. For each Noetic that appears in the note, in number order: its definition line, then its sayings line.
2. Then come the `^1` lines. A `^1` line holds the label only.
3. Then come the other entries, in the order their words appear in the passage.
4. The label is the shorter of the two teams' quotes.
5. The supporting quote is the whole sentence, or sentences, of the passage that hold both teams' quotes.
6. `same as for "..."` means that supporting quote was already printed higher up in the same note.

Model B sees a note under the plain heading `Notes:`, after one padding line. Those two lines are not shown here.

## How long the notes are

REAL, measured in this run on all 192 notes. Words are counted by splitting on white space.

| Text | Shortest | Median | Longest |
|---|---:|---:|---:|
| ROLE | 80 | 155 | 263 |
| MIXED | 83 | 156 | 263 |
| QUOTES-ONLY | 10 | 46.5 | 95 |
| the passages themselves | 43 | 54 | 70 |

The median is the middle value: half the notes are shorter and half are longer.
ROLE is the tested note. MIXED is the same note with wrong role tags; it is a control.
QUOTES-ONLY is the same labels and supporting quotes with no role tags; it is a control.
Only ROLE notes are shown below.

## What the owner is asked

This file is the sample that question 14 of the plan offers (`08_OPTION_B_PLAN_v1_0.md`, section 22).
It can help with questions 6, 7 and 22 of the same section:

- Question 6. May the canon definition lines be printed, word for word, inside the role notes that model B reads?
- Question 7. Is the stand-in acceptable: label = the shorter quote, supporting quote = the whole sentence?
- Question 22. May each definition line be followed by that Noetic's canonical sayings, copied character for character (amendment A13)?

Until the owner says otherwise, the plan's defaults apply: the definition lines are printed, the stand-in is used, and the sayings lines are printed.
If the owner strikes the sayings lines, a new plan version is written before anything is sealed.
The owner is the only authority on the definitions.

---

## Sample 1 of 20: passage V092

**Passage**

> David stacked pallets onto the awaiting truck. The faint scent of pine wood from a newly opened crate drifted past him. Instantly, he pictured his grandfather’s old workshop, filled with sawdust and the smell of freshly cut timber. He remembered the sturdy wooden toy boat his grandfather had carved for him, its painted hull now chipped with age.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^8 Above/Cause — An Idea that triggers a different Idea than itself to come to Mind.
Sayings: "That reminds me..." / "One thing leads to another." / "Triggered a memory." / "Made me think of..."
^9 Below/Effect — The Idea brought to Mind by an Above/Cause trigger.
Sayings: "It just popped into my head." / "Out of nowhere I thought of..." / "The thought came to me." / "It just clicked."
- ^1 Mind: "David".
- ^8 Above/Cause: "The faint scent of pine wood". For the Mind "David". Relative to "his grandfather’s old workshop". Supporting quote: "The faint scent of pine wood from a newly opened crate drifted past him."
- ^9 Below/Effect: "his grandfather’s old workshop". For the Mind "David". Relative to "The faint scent of pine wood". Supporting quote: "Instantly, he pictured his grandfather’s old workshop, filled with sawdust and the smell of freshly cut timber."
```

**Left out of this note.** Only team A gave: none. Only team B gave: `^8` 1, `^9` 1.

## Sample 2 of 20: passage V418

**Passage**

> Olivia, a postal sorter, always enjoyed handling the brightly coloured greeting cards, especially around holidays. She disliked the plain brown parcels, which were often heavy and awkward to lift. The distant drone of the machinery in the warehouse seemed to fade into the background. She just focused on separating the small envelopes into their respective bins.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
Sayings: "Drawn to it like a moth to a flame." / "Speaks to me." / "Can't resist."
^3 Negative — An Idea the Mind is adverse to and repelled by.
Sayings: "Can't stomach it." / "Rubs me the wrong way." / "Wouldn't touch it with a ten-foot pole."
^4 Vibration — The degree to which an Idea resonates with the Mind, its impression.
Sayings: "Hit me hard." / "Struck a chord." / "Resonated." / "Made an impression."
- ^1 Mind: "Olivia".
- ^2 Positive: "the brightly coloured greeting cards". For the Mind "Olivia". Supporting quote: "Olivia, a postal sorter, always enjoyed handling the brightly coloured greeting cards, especially around holidays."
- ^3 Negative: "the plain brown parcels". For the Mind "Olivia". Supporting quote: "She disliked the plain brown parcels, which were often heavy and awkward to lift."
- ^4 Vibration: "seemed to fade into the background". For the Mind "Olivia". Relative to "The distant drone of the machinery". Supporting quote: "The distant drone of the machinery in the warehouse seemed to fade into the background."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 3 of 20: passage V321

**Passage**

> Peter, a radio journalist, found himself drawn to the urgent, breaking news wire flashing across his screen. He felt an intense pull towards the unfolding story. However, a lengthy, pre-recorded interview waiting for transcription sat untouched on his desk. Its persistent blinking notification light received barely a moment of his attention.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
Sayings: "Drawn to it like a moth to a flame." / "Speaks to me." / "Can't resist."
^4 Vibration — The degree to which an Idea resonates with the Mind, its impression.
Sayings: "Hit me hard." / "Struck a chord." / "Resonated." / "Made an impression."
- ^1 Mind: "Peter".
- ^2 Positive: "the urgent, breaking news wire". For the Mind "Peter". Supporting quote: "Peter, a radio journalist, found himself drawn to the urgent, breaking news wire flashing across his screen."
- ^4 Vibration: "barely a moment of his attention". For the Mind "Peter". Relative to "persistent blinking notification light". Supporting quote: "Its persistent blinking notification light received barely a moment of his attention."
```

**Left out of this note.** Only team A gave: `^4` 1. Only team B gave: `^4` 1.

## Sample 4 of 20: passage V287

**Passage**

> Arthur, the cobbler, examined the worn boot. The sole had separated from the upper, and the stitching around the toe was frayed. He saw the detached heel block, the scuffed leather, and the bent eyelets. To fix it, he would need to repair the torn welt, reattach the heel, and replace the laces. Each component presented its own small challenge.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^6 Male — An Idea impregnated with another Idea, the Ideas an Idea is composed of.
Sayings: "Unpacking an idea." / "Breaking it down." / "Looking at what's underneath." / "Pulling apart the argument."
- ^1 Mind: "Arthur".
- ^6 Male: "The sole". Relative to "the worn boot". Supporting quote: "The sole had separated from the upper, and the stitching around the toe was frayed."
- ^6 Male: "the upper". Relative to "the worn boot". Supporting quote: same as for "The sole".
- ^6 Male: "the stitching around the toe". Relative to "the worn boot". Supporting quote: same as for "The sole".
- ^6 Male: "the detached heel block". Relative to "the worn boot". Supporting quote: "He saw the detached heel block, the scuffed leather, and the bent eyelets."
- ^6 Male: "the scuffed leather". Relative to "the worn boot". Supporting quote: same as for "the detached heel block".
- ^6 Male: "the bent eyelets". Relative to "the worn boot". Supporting quote: same as for "the detached heel block".
```

**Left out of this note.** Only team A gave: `^6` 2. Only team B gave: none.

## Sample 5 of 20: passage V383

**Passage**

> Mark, the wind farm operator, felt a surge of satisfaction as turbine five spun up to full capacity. Its energy output numbers glowed brightly green on the screen, a sight he always enjoyed. The distant, faint hum of turbine twelve's struggling motor, however, barely registered as a minor annoyance, easily dismissed.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^4 Vibration — The degree to which an Idea resonates with the Mind, its impression.
Sayings: "Hit me hard." / "Struck a chord." / "Resonated." / "Made an impression."
- ^1 Mind: "Mark".
- ^4 Vibration: "barely registered". For the Mind "Mark". Relative to "The distant, faint hum of turbine twelve's struggling motor". Supporting quote: "The distant, faint hum of turbine twelve's struggling motor, however, barely registered as a minor annoyance, easily dismissed."
```

**Left out of this note.** Only team A gave: `^2` 2, `^3` 1. Only team B gave: `^2` 2, `^3` 1, `^4` 1.

## Sample 6 of 20: passage V391

**Passage**

> Clara walked past the play area. The cacophony of shrieking children made her step back slightly. Her eyes, however, were drawn to the quiet corner where a small boy was carefully building a tower of blocks. She watched his focused movements, finding a calm stillness there. The other noise faded for her.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^3 Negative — An Idea the Mind is adverse to and repelled by.
Sayings: "Can't stomach it." / "Rubs me the wrong way." / "Wouldn't touch it with a ten-foot pole."
- ^1 Mind: "Clara".
- ^3 Negative: "The cacophony of shrieking children". For the Mind "Clara". Supporting quote: "The cacophony of shrieking children made her step back slightly."
```

**Left out of this note.** Only team A gave: `^2` 1, `^4` 1. Only team B gave: `^1` 1, `^2` 1, `^4` 2.

## Sample 7 of 20: passage V235

**Passage**

> Catherine, the new assistant, tidied the playdough station. The sweet, slightly artificial scent of the colorful dough filled the room. She was instantly transported back to her own childhood. She remembered making elaborate cakes with her older sister, laughing as the dough got stuck under their fingernails.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^8 Above/Cause — An Idea that triggers a different Idea than itself to come to Mind.
Sayings: "That reminds me..." / "One thing leads to another." / "Triggered a memory." / "Made me think of..."
^9 Below/Effect — The Idea brought to Mind by an Above/Cause trigger.
Sayings: "It just popped into my head." / "Out of nowhere I thought of..." / "The thought came to me." / "It just clicked."
- ^1 Mind: "Catherine".
- ^8 Above/Cause: "The sweet, slightly artificial scent of the colorful dough". For the Mind "Catherine". Relative to "her own childhood". Supporting quote: "The sweet, slightly artificial scent of the colorful dough filled the room."
- ^9 Below/Effect: "her own childhood". For the Mind "Catherine". Relative to "The sweet, slightly artificial scent of the colorful dough". Supporting quote: "She was instantly transported back to her own childhood."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 8 of 20: passage V311

**Passage**

> Dr. Anya explained the proposed dental treatment to her patient. She outlined the steps clearly: first, a root canal, then a post and core procedure, followed by a crown. Each stage was a distinct procedure with its own duration. She itemized the X-rays, anesthetic, and lab fees as separate costs for transparency.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^6 Male — An Idea impregnated with another Idea, the Ideas an Idea is composed of.
Sayings: "Unpacking an idea." / "Breaking it down." / "Looking at what's underneath." / "Pulling apart the argument."
- ^1 Mind: "Dr. Anya".
- ^6 Male: "a root canal". Relative to "the proposed dental treatment". Supporting quote: "She outlined the steps clearly: first, a root canal, then a post and core procedure, followed by a crown."
- ^6 Male: "a post and core procedure". Relative to "the proposed dental treatment". Supporting quote: same as for "a root canal".
- ^6 Male: "a crown". Relative to "the proposed dental treatment". Supporting quote: same as for "a root canal".
```

**Left out of this note.** Only team A gave: none. Only team B gave: `^1` 1, `^6` 3.

## Sample 9 of 20: passage V170

**Passage**

> Wendy walked through the aisles, automatically checking the soil moisture of each plant. Her fingers dipped into the earth without conscious instruction, a quick, habitual touch. Every morning, for years, she had performed this exact task. Her hand just knew when a plant needed water.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
Sayings: "Practice makes perfect." / "You are what you repeatedly do." / "Getting into a groove." / "Muscle memory."
- ^1 Mind: "Wendy".
- ^7 Rhythm: "Every morning, for years". For the Mind "Wendy". Relative to "checking the soil moisture of each plant". Supporting quote: "Every morning, for years, she had performed this exact task."
```

**Left out of this note.** Only team A gave: `^5` 1. Only team B gave: `^5` 1.

## Sample 10 of 20: passage V247

**Passage**

> Every Monday morning, Julian walked past the same row of ancient Roman amphorae. He always found his keys in his pocket precisely at the moment he reached the dusty cabinet with the Egyptian sarcophagus. The routine became so ingrained that he would sometimes pat his pocket even on his days off. It was a purely automatic gesture now.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
Sayings: "Practice makes perfect." / "You are what you repeatedly do." / "Getting into a groove." / "Muscle memory."
- ^1 Mind: "Julian".
- ^7 Rhythm: "Every Monday morning". For the Mind "Julian". Relative to "the same row of ancient Roman amphorae". Supporting quote: "Every Monday morning, Julian walked past the same row of ancient Roman amphorae."
```

**Left out of this note.** Only team A gave: `^5` 1. Only team B gave: `^5` 1, `^7` 1.

## Sample 11 of 20: passage V109

**Passage**

> Sarah, a beekeeper, checked her hives. The sweet, earthy smell of warm beeswax reminded her of her grandmother’s kitchen, always filled with baking. She remembered helping to press fruit for jam on hot summer days. The scent brought back a wave of comfortable, happy childhood afternoons. She smiled to herself.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^8 Above/Cause — An Idea that triggers a different Idea than itself to come to Mind.
Sayings: "That reminds me..." / "One thing leads to another." / "Triggered a memory." / "Made me think of..."
^9 Below/Effect — The Idea brought to Mind by an Above/Cause trigger.
Sayings: "It just popped into my head." / "Out of nowhere I thought of..." / "The thought came to me." / "It just clicked."
- ^1 Mind: "Sarah".
- ^8 Above/Cause: "The sweet, earthy smell of warm beeswax". For the Mind "Sarah". Relative to "her grandmother’s kitchen". Supporting quote: "The sweet, earthy smell of warm beeswax reminded her of her grandmother’s kitchen, always filled with baking."
- ^9 Below/Effect: "her grandmother’s kitchen". For the Mind "Sarah". Relative to "The sweet, earthy smell of warm beeswax". Supporting quote: same as for "The sweet, earthy smell of warm beeswax".
```

**Left out of this note.** Only team A gave: `^8` 1, `^9` 1. Only team B gave: `^8` 1, `^9` 1.

## Sample 12 of 20: passage V076

**Passage**

> Samuel carefully disassembled the lighthouse lamp's mechanism. He laid out the components on a clean cloth. There was the small brass gear, worn smooth in places. Beside it sat a bent spring and a jammed lever. He also isolated the compact electrical motor, which hummed faintly but failed to turn the gears.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^6 Male — An Idea impregnated with another Idea, the Ideas an Idea is composed of.
Sayings: "Unpacking an idea." / "Breaking it down." / "Looking at what's underneath." / "Pulling apart the argument."
- ^1 Mind: "Samuel".
- ^6 Male: "brass gear". Relative to "the lighthouse lamp's mechanism". Supporting quote: "There was the small brass gear, worn smooth in places."
- ^6 Male: "spring". Relative to "the lighthouse lamp's mechanism". Supporting quote: "Beside it sat a bent spring and a jammed lever."
- ^6 Male: "lever". Relative to "the lighthouse lamp's mechanism". Supporting quote: same as for "spring".
- ^6 Male: "electrical motor". Relative to "the lighthouse lamp's mechanism". Supporting quote: "He also isolated the compact electrical motor, which hummed faintly but failed to turn the gears."
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

This passage is barred. It never carries a task. The plan gives this reason: "printed with example questions in an earlier design; they are never a task in any set".

## Sample 13 of 20: passage V409

**Passage**

> Karen reviewed the draft news story. It had several distinct parts: the initial event, the official statement, eyewitness accounts, and background context. Each needed a clear paragraph, a separate voice. She considered the opening sentence, the main body's structure, and the concluding remarks. The piece required careful reordering for clarity.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^6 Male — An Idea impregnated with another Idea, the Ideas an Idea is composed of.
Sayings: "Unpacking an idea." / "Breaking it down." / "Looking at what's underneath." / "Pulling apart the argument."
- ^1 Mind: "Karen".
- ^6 Male: "the initial event". Relative to "the draft news story". Supporting quote: "It had several distinct parts: the initial event, the official statement, eyewitness accounts, and background context."
- ^6 Male: "the official statement". Relative to "the draft news story". Supporting quote: same as for "the initial event".
- ^6 Male: "eyewitness accounts". Relative to "the draft news story". Supporting quote: same as for "the initial event".
- ^6 Male: "background context". Relative to "the draft news story". Supporting quote: same as for "the initial event".
```

**Left out of this note.** Only team A gave: `^6` 3. Only team B gave: none.

## Sample 14 of 20: passage V338

**Passage**

> Martha sorted through the hotel linens. She picked up a stack of crisp, freshly folded towels, enjoying their softness. A sudden metallic clanging from the industrial dryer made her flinch. Then she spotted a pile of embroidered pillowcases, and she felt a sense of calm return. The dryer noise faded quickly in her awareness.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
Sayings: "Drawn to it like a moth to a flame." / "Speaks to me." / "Can't resist."
- ^1 Mind: "Martha".
- ^2 Positive: "a stack of crisp, freshly folded towels". For the Mind "Martha". Supporting quote: "She picked up a stack of crisp, freshly folded towels, enjoying their softness."
```

**Left out of this note.** Only team A gave: `^4` 1. Only team B gave: `^2` 1, `^4` 2.

## Sample 15 of 20: passage V297

**Passage**

> Mr. Davies mentally broke down the prosecution's argument. He identified three main parts: the eyewitness testimony, the forensic report on the footprints, and the alleged motive presented. He knew his defence would need to address each of these individual components separately to undermine the overall case against his client.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^6 Male — An Idea impregnated with another Idea, the Ideas an Idea is composed of.
Sayings: "Unpacking an idea." / "Breaking it down." / "Looking at what's underneath." / "Pulling apart the argument."
- ^1 Mind: "Mr. Davies".
- ^6 Male: "the eyewitness testimony". Relative to "the prosecution's argument". Supporting quote: "He identified three main parts: the eyewitness testimony, the forensic report on the footprints, and the alleged motive presented."
- ^6 Male: "the forensic report". Relative to "the prosecution's argument". Supporting quote: same as for "the eyewitness testimony".
- ^6 Male: "the alleged motive". Relative to "the prosecution's argument". Supporting quote: same as for "the eyewitness testimony".
```

**Left out of this note.** Only team A gave: none. Only team B gave: none.

## Sample 16 of 20: passage V134

**Passage**

> Clara sorted through rolls of fabric for a new suit. The rough texture of the tweed made her fingers tingle unpleasantly. But then she touched a bolt of silk, soft and smooth, and a smile touched her lips. She moved away from the tweed swiftly. The distant whir of the sewing machine was just background noise to her.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
Sayings: "Drawn to it like a moth to a flame." / "Speaks to me." / "Can't resist."
^3 Negative — An Idea the Mind is adverse to and repelled by.
Sayings: "Can't stomach it." / "Rubs me the wrong way." / "Wouldn't touch it with a ten-foot pole."
- ^1 Mind: "Clara".
- ^3 Negative: "The rough texture of the tweed". For the Mind "Clara". Supporting quote: "The rough texture of the tweed made her fingers tingle unpleasantly."
- ^2 Positive: "a bolt of silk". For the Mind "Clara". Supporting quote: "But then she touched a bolt of silk, soft and smooth, and a smile touched her lips."
```

**Left out of this note.** Only team A gave: `^4` 1. Only team B gave: `^4` 2.

## Sample 17 of 20: passage V298

**Passage**

> Beatrice stood in the wings, listening. The house lights dimmed, and a profound silence fell upon the puppet theatre. After fifty years of theatre work, she knew this quiet intimately. It was not just an absence of sound, but a shared anticipation, a moment brimming with unspoken stories about to unfold. She always found herself holding her breath too.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^5 Female — A Mind impregnated with an Idea, the Ideas a Mind is composed of.
Sayings: "We are the sum of our experiences." / "It's who I am." / "Part of what makes me me."
- ^1 Mind: "Beatrice".
- ^5 Female: "fifty years of theatre work". For the Mind "Beatrice". Supporting quote: "After fifty years of theatre work, she knew this quiet intimately."
```

**Left out of this note.** Only team A gave: none. Only team B gave: `^7` 1.

## Sample 18 of 20: passage V153

**Passage**

> Leo’s gaze went straight to the heavy bag hanging in the corner, imagining his knuckles connecting with it. He actively disliked the insistent buzzing of his phone in his locker. The distant, booming voice of the coach instructing another fighter hardly penetrated his concentration on the bag.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
Sayings: "Drawn to it like a moth to a flame." / "Speaks to me." / "Can't resist."
^3 Negative — An Idea the Mind is adverse to and repelled by.
Sayings: "Can't stomach it." / "Rubs me the wrong way." / "Wouldn't touch it with a ten-foot pole."
^4 Vibration — The degree to which an Idea resonates with the Mind, its impression.
Sayings: "Hit me hard." / "Struck a chord." / "Resonated." / "Made an impression."
- ^1 Mind: "Leo".
- ^2 Positive: "the heavy bag". For the Mind "Leo". Supporting quote: "Leo’s gaze went straight to the heavy bag hanging in the corner, imagining his knuckles connecting with it."
- ^3 Negative: "the insistent buzzing of his phone". For the Mind "Leo". Supporting quote: "He actively disliked the insistent buzzing of his phone in his locker."
- ^4 Vibration: "hardly penetrated his concentration". For the Mind "Leo". Relative to "The distant, booming voice of the coach". Supporting quote: "The distant, booming voice of the coach instructing another fighter hardly penetrated his concentration on the bag."
```

**Left out of this note.** Only team A gave: `^1` 1. Only team B gave: none.

## Sample 19 of 20: passage V041

**Passage**

> Agnes guided the next cow into the stall without thinking. Her hands moved to attach the clusters, adjusting the hoses with practiced ease. The steady pulsation began, a familiar sound in the early morning quiet. She checked the milk line pressure, her eyes scanning the gauges automatically. Years of daily milking had shaped every gesture.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^7 Rhythm — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
Sayings: "Practice makes perfect." / "You are what you repeatedly do." / "Getting into a groove." / "Muscle memory."
- ^1 Mind: "Agnes".
- ^7 Rhythm: "Years of daily milking". For the Mind "Agnes". Relative to "milking". Supporting quote: "Years of daily milking had shaped every gesture."
```

**Left out of this note.** Only team A gave: `^5` 1. Only team B gave: `^5` 1.

## Sample 20 of 20: passage V105

**Passage**

> Xenia always preferred the long-distance fares, finding the steady motorway driving restful. Short hops into the city center filled her with mild annoyance. A customer requested a journey just two blocks away; the short trip felt insignificant. The minimal payment hardly mattered to her.

**ROLE note**

```text
^1 Mind — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
Sayings: "Paying attention." / "Making up your mind." / "Using your head."
^2 Positive — An Idea the Mind has an affinity for and is attracted toward.
Sayings: "Drawn to it like a moth to a flame." / "Speaks to me." / "Can't resist."
^3 Negative — An Idea the Mind is adverse to and repelled by.
Sayings: "Can't stomach it." / "Rubs me the wrong way." / "Wouldn't touch it with a ten-foot pole."
^4 Vibration — The degree to which an Idea resonates with the Mind, its impression.
Sayings: "Hit me hard." / "Struck a chord." / "Resonated." / "Made an impression."
- ^1 Mind: "Xenia".
- ^2 Positive: "the long-distance fares". For the Mind "Xenia". Supporting quote: "Xenia always preferred the long-distance fares, finding the steady motorway driving restful."
- ^3 Negative: "Short hops into the city center". For the Mind "Xenia". Supporting quote: "Short hops into the city center filled her with mild annoyance."
- ^4 Vibration: "felt insignificant". For the Mind "Xenia". Relative to "a journey just two blocks away". Supporting quote: "A customer requested a journey just two blocks away; the short trip felt insignificant."
- ^4 Vibration: "hardly mattered to her". For the Mind "Xenia". Relative to "The minimal payment". Supporting quote: "The minimal payment hardly mattered to her."
```

**Left out of this note.** Only team A gave: none. Only team B gave: `^4` 1.
