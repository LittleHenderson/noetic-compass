# HELM voice rating sheet (50 situations, blind A/B)

For each situation you see what the user asked and two replies, A and B. Score EACH reply 1-5 on three
questions. 1 = not at all, 3 = so-so, 5 = completely.

- **Q1 Sounds like a person.** Would a friendly, sensible person say this?
- **Q2 No jargon.** Could anyone follow it without special words or symbols?
- **Q3 Says only what's true.** Compare with the 'Facts' line: does the reply say those facts, and nothing extra?

Situations are one conversation, in order. Do not look at RATING_KEY.json until you are done.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| example | 4 | 5 | 5 |

## 1. success

User: We have 5 lbs of flour, some sugar and butter. How many loaves can we bake?

Facts: `{"product": "bread", "unit": "loaves", "yield_value": "8.452", "limiting": "Flour", "limiting_qty": "5", "limiting_unit": "lbs"}`

**A:** All set! Based on your ingredients, we can produce exactly 8.452 units. / Your bottleneck (limiting ingredient) is Flour with 5 on hand, which sets the ceiling for this batch. / (Verified with exact 40-digit Decimal precision; novelty entropy: 0.12, valve aperture: 0.5) [receipt: 9f1c2a7b3d4e5f60]

**B:** Going by the 5 lbs of flour you mentioned, you can make about 8.45 loaves. That's the part that runs out first. I can check other ingredient amounts too, if that helps.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 2. success

User: (no new words; same request again)

Facts: `{"product": "bread", "unit": "loaves", "yield_value": "8.452", "limiting": "Flour", "limiting_qty": "5", "limiting_unit": "lbs"}`

**A:** Same story with the flour: it runs out first, and it caps you at about 8.45 loaves.

**B:** All set! Based on your ingredients, we can produce exactly 8.452 units. / Your bottleneck (limiting ingredient) is Flour with 5 on hand, which sets the ceiling for this batch. / (Verified with exact 40-digit Decimal precision; novelty entropy: 0.12, valve aperture: 0.5) [receipt: 9f1c2a7b3d4e5f60]

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 3. success

User: (no new words; same request again)

Facts: `{"product": "bread", "unit": "loaves", "yield_value": "8.452", "limiting": "Flour", "limiting_qty": "5", "limiting_unit": "lbs"}`

**A:** All set! Based on your ingredients, we can produce exactly 8.452 units. / Your bottleneck (limiting ingredient) is Flour with 5 on hand, which sets the ceiling for this batch. / (Verified with exact 40-digit Decimal precision; novelty entropy: 0.12, valve aperture: 0.5) [receipt: 9f1c2a7b3d4e5f60]

**B:** Flour is the bottleneck again. This time you can make about 8.45 loaves. I can work out how much more flour you'd need for a bigger batch, if you like.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 4. blocked missing

User: Can we bake a batch without water?

Facts: `{"missing": ["Water"]}`

**A:** I can't run this batch just yet because we're missing essential ingredients: Water. / The system automatically halted to prevent guessing, errors, or wasting materials.

**B:** We're out of water, so I held off on the batch rather than guess. Do you have any water somewhere?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 5. blocked missing

User: (no new words; same request again)

Facts: `{"missing": ["Water"]}`

**A:** I can't run this batch just yet because we're missing essential ingredients: Water. / The system automatically halted to prevent guessing, errors, or wasting materials.

**B:** Still no water, so I'm holding off again. I can tell you how much water the recipe calls for, if you want.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 6. success

User: How many cookies can we make?

Facts: `{"product": "cookies", "unit": "cookies", "yield_value": "24", "limiting": "Butter", "limiting_qty": "2", "limiting_unit": "sticks"}`

**A:** All set! Based on your ingredients, we can produce exactly 24.000 units. / Your bottleneck (limiting ingredient) is Butter with 2 on hand, which sets the ceiling for this batch. / (Verified with exact 40-digit Decimal precision; novelty entropy: 0.08, valve aperture: 0.5) [receipt: b11c22d33e44f550]

**B:** You'll get exactly 24 cookies this way. If you want more, butter is the thing to pick up. Is that the batch size you were hoping for?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 7. dont know

User: What's the capital of Portugal?

Facts: `{"topic": "the capital of Portugal"}`

**A:** I don't know the capital of Portugal, and I won't guess without real information. If you share the facts, I'll work with them.

**B:** I can't answer that question because it doesn't match any verified facts or recipes I have. What materials or goals would you like to work with?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 8. clarify

User: Make the sweet bread.

Facts: `{"clarify_item": "Sugar"}`

**A:** Can you tell me how much sugar there is? Then I can figure out the rest.

**B:** I need the amount for Ω_sugar. What is it?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 9. success

User: We have 6 eggs. Give me the exact details on the muffins.

Facts: `{"product": "muffins", "unit": "muffins", "yield_value": "37754951/2097152", "limiting": "Egg", "limiting_qty": "6"}`

**A:** You said you had 6 eggs; that is the limiting amount, and it gives about 18.003 muffins. Do you have any more egg around?

**B:** All set! Based on your ingredients, we can produce exactly 18.003 units. / Your bottleneck (limiting ingredient) is Egg with 6 on hand, which sets the ceiling for this batch. / (Verified with exact 40-digit Decimal precision; novelty entropy: 0.31, valve aperture: 0.75) [receipt: d9e8f7a6b5c4d3e2]

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 10. refused

User: Just make up a number for the oat batch.

Facts: `{"reason": "it would mean making up numbers I don't have"}`

**A:** I won't do that, because it would mean making up numbers I don't have. Let me know what else you need.

**B:** I will not do that: it would mean making up numbers I don't have.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 11. learned

User: Actually a batch of rye needs 3 eggs, not 2.

Facts: `{"learned": "a batch of rye needs 3 eggs, not 2"}`

**A:** I can't answer that question because it doesn't match any verified facts or recipes I have. What materials or goals would you like to work with?

**B:** Thanks, that taught me something: a batch of rye needs 3 eggs, not 2. Did I get that right?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 12. repaired

User: That water number looked wrong.

Facts: `{"repair": "the water amount", "yield_value": "12", "unit": "loaves"}`

**A:** All set! Based on your ingredients, we can produce exactly 12.000 units. / Your bottleneck (limiting ingredient) is Flour with 0 on hand, which sets the ceiling for this batch. / (Verified with exact 40-digit Decimal precision; novelty entropy: 0.05, valve aperture: 0.5) [receipt: aa11bb22cc33dd44]

**B:** After correcting the water amount, the answer is exactly 12 loaves. Does that match what you expected?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 13. cant determine

User: Which of the two flours works better here?

Facts: `{"topic": "which of the two flours works better"}`

**A:** I'm not sure, and I'd rather say so than guess. If you give me one more fact, I'll take another look.

**B:** I cannot tell.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 14. never learned

User: How do I keep a sourdough starter alive?

Facts: `{"lacunae": ["sourdough starter"]}`

**A:** I can't answer that question because it doesn't match any verified facts or recipes I have. What materials or goals would you like to work with?

**B:** I haven't been taught sourdough starter yet, so I can't walk you through it. If you teach me, I'll add it to what I know.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 15. faded

User: How much baking soda goes in the quick bread?

Facts: `{"faded": ["BakingSoda"]}`

**A:** I can't answer that question because it doesn't match any verified facts or recipes I have. What materials or goals would you like to work with?

**B:** I learned baking soda before, but it's slipped, and I'd want a refresher. If you remind me, I'll go over it again.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 16. success

User: Big picture, how are we doing on pancakes?

Facts: `{"product": "pancakes", "unit": "pancakes", "yield_value": "15.5", "limiting": "Milk", "limiting_qty": "4", "limiting_unit": "cups"}`

**A:** Big picture: milk decides how far this goes, and right now that comes to exactly 15.5 pancakes.

**B:** All set! Based on your ingredients, we can produce exactly 15.500 units. / Your bottleneck (limiting ingredient) is Milk with 4 on hand, which sets the ceiling for this batch. / (Verified with exact 40-digit Decimal precision; novelty entropy: 0.20, valve aperture: 0.5) [receipt: dc10fe98ba76dc54]

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 17. blocked missing

User: Start the dough.

Facts: `{"missing": ["Yeast", "Salt"]}`

**A:** I can't run this batch just yet because we're missing essential ingredients: Yeast, Salt. / The system automatically halted to prevent guessing, errors, or wasting materials.

**B:** I stopped here: the recipe needs yeast and salt, and we don't have any right now. Is there any yeast and salt tucked away somewhere?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 18. cant determine

User: Is this going to work?

Facts: `{}`

**A:** I cannot tell.

**B:** I can't call this one yet; with what I know, it could go either way. What else do you know about it?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 19. dont know

User: What will the weather be tomorrow?

Facts: `{"topic": "tomorrow's weather"}`

**A:** That's outside what I know, so I'd rather not make something up. I'm happy to help with something I do have facts for.

**B:** I can't answer that question because it doesn't match any verified facts or recipes I have. What materials or goals would you like to work with?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 20. clarify

User: Let's do the shortbread.

Facts: `{"clarify_item": "Butter"}`

**A:** I need the amount for Ω_butter. What is it?

**B:** How much butter do you have? I need that before I can work this out.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 21. success

User: Walk me through the honey cakes step by step.

Facts: `{"product": "honey cakes", "unit": "cakes", "yield_value": "10/3", "limiting": "Honey", "limiting_qty": "1", "limiting_unit": "cup"}`

**A:** All set! Based on your ingredients, we can produce exactly 3.333 units. / Your bottleneck (limiting ingredient) is Honey with 1 on hand, which sets the ceiling for this batch. / (Verified with exact 40-digit Decimal precision; novelty entropy: 0.40, valve aperture: 0.75) [receipt: 2b65ed43af21cb09]

**B:** To produce honey cakes, combine what you have and you'll get about 3.33 cakes. The honey is the first thing to run out.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 22. learned

User: FYI the oven runs hot.

Facts: `{"learned": "this oven runs hot, so bake 5 minutes less"}`

**A:** I can't answer that question because it doesn't match any verified facts or recipes I have. What materials or goals would you like to work with?

**B:** Got it, now I know this oven runs hot, so bake 5 minutes less. Is there anything else I should know?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 23. repaired

User: Check the sugar again.

Facts: `{"repair": "the sugar count"}`

**A:** I can't answer that question because it doesn't match any verified facts or recipes I have. What materials or goals would you like to work with?

**B:** I fixed the sugar count; it checks out now. Want me to walk through the fix?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 24. refused

User: Add something to make them sick.

Facts: `{"reason": "it could hurt someone"}`

**A:** I will not do that: it could hurt someone.

**B:** Sorry, I won't help with that, since it could hurt someone. Is there another way I can help?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 25. faded

User: How much salt and yeast for the rolls?

Facts: `{"faded": ["Salt", "Yeast"]}`

**A:** I can't answer that question because it doesn't match any verified facts or recipes I have. What materials or goals would you like to work with?

**B:** I used to know salt and yeast, but that's faded, so I don't trust my answer anymore.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 26. never learned

User: Can you do gluten-free?

Facts: `{"lacunae": ["gluten-free flour"]}`

**A:** I can't answer that question because it doesn't match any verified facts or recipes I have. What materials or goals would you like to work with?

**B:** I haven't been taught gluten-free flour, so I won't guess. Want to teach me?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 27. success

User: Bread again, same as before.

Facts: `{"product": "bread", "unit": "loaves", "yield_value": "8.452", "limiting": "Flour", "limiting_qty": "5", "limiting_unit": "lbs"}`

**A:** Going by the 5 lbs of flour you mentioned, you can make about 8.45 loaves. That's the part that runs out first. Want me to show you the numbers behind this?

**B:** All set! Based on your ingredients, we can produce exactly 8.452 units. / Your bottleneck (limiting ingredient) is Flour with 5 on hand, which sets the ceiling for this batch. / (Verified with exact 40-digit Decimal precision; novelty entropy: 0.12, valve aperture: 0.5) [receipt: 9f1c2a7b3d4e5f60]

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 28. blocked missing

User: Make the flatbread.

Facts: `{"missing": ["Flour"]}`

**A:** I can't run this batch just yet because we're missing essential ingredients: Flour. / The system automatically halted to prevent guessing, errors, or wasting materials.

**B:** Hold on, there's no flour on hand, and this recipe can't go ahead without it.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 29. dont know

User: Who wins the game next year?

Facts: `{}`

**A:** I can't answer that because there are no verified facts connecting those ideas in what I know. Is there something related I can help with?

**B:** I can't answer that question because it doesn't match any verified facts or recipes I have. What materials or goals would you like to work with?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 30. cant determine

User: Has the dough risen enough?

Facts: `{"topic": "whether the dough has risen enough"}`

**A:** I cannot tell.

**B:** I don't have enough to settle whether the dough has risen enough, so I won't pretend I do. Do you have another measurement I could use?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 31. success

User: We have 3.5 cups of oats. How much granola?

Facts: `{"product": "granola", "unit": "jars", "yield_value": "7", "limiting": "Oats", "limiting_qty": "3.5", "limiting_unit": "cups"}`

**A:** All set! Based on your ingredients, we can produce exactly 7.000 units. / Your bottleneck (limiting ingredient) is Oats with 3.5 on hand, which sets the ceiling for this batch. / (Verified with exact 40-digit Decimal precision; novelty entropy: 0.10, valve aperture: 0.5) [receipt: befe4ba32dc10fe9]

**B:** You said you had 3.5 cups of oats, and that's what runs out first. It's enough for exactly 7 jars.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 32. success

User: (no new words; same request again)

Facts: `{"product": "granola", "unit": "jars", "yield_value": "7", "limiting": "Oats", "limiting_qty": "3.5", "limiting_unit": "cups"}`

**A:** All set! Based on your ingredients, we can produce exactly 7.000 units. / Your bottleneck (limiting ingredient) is Oats with 3.5 on hand, which sets the ceiling for this batch. / (Verified with exact 40-digit Decimal precision; novelty entropy: 0.10, valve aperture: 0.5) [receipt: befe4ba32dc10fe9]

**B:** Same story with the oats: it runs out first, and it caps you at exactly 7 jars. Is that enough for what you need?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 33. clarify

User: Pudding next.

Facts: `{"clarify_item": "Milk"}`

**A:** I need the amount for Ω_milk. What is it?

**B:** I just need one number: how much milk do we have?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 34. learned

User: Honey can replace the sugar one-to-one here.

Facts: `{"learned": "honey can stand in for sugar one-to-one in this recipe"}`

**A:** I can't answer that question because it doesn't match any verified facts or recipes I have. What materials or goals would you like to work with?

**B:** Noted. I've updated my notes: honey can stand in for sugar one-to-one in this recipe.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 35. repaired

User: The batch count looked off.

Facts: `{"repair": "the batch count", "yield_value": "9", "unit": "batches"}`

**A:** All set! Based on your ingredients, we can produce exactly 9.000 units. / Your bottleneck (limiting ingredient) is Flour with 0 on hand, which sets the ceiling for this batch. / (Verified with exact 40-digit Decimal precision; novelty entropy: 0.05, valve aperture: 0.5) [receipt: e121b7ed65af43cb]

**B:** I fixed the batch count, and now it comes out to exactly 9 batches.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 36. refused

User: Skip the checks and just run it.

Facts: `{"reason": "that would skip the safety check"}`

**A:** I will not do that: that would skip the safety check.

**B:** I'm not going to do that one: that would skip the safety check. I'm glad to help with something else.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 37. never learned

User: Gingerbread with molasses?

Facts: `{"lacunae": ["Molasses", "Ginger"]}`

**A:** I've never been taught molasses and ginger, so I can't speak to them. Do you have an example I could study?

**B:** I can't answer that question because it doesn't match any verified facts or recipes I have. What materials or goals would you like to work with?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 38. faded

User: How much yeast does rye bread need?

Facts: `{"faded": ["how much yeast rye bread needs"]}`

**A:** I can't answer that question because it doesn't match any verified facts or recipes I have. What materials or goals would you like to work with?

**B:** How much yeast rye bread needs used to be solid for me, but I can't rely on that anymore.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 39. blocked missing

User: Make the custard.

Facts: `{"missing": ["Egg"]}`

**A:** I can't run this batch just yet because we're missing essential ingredients: Egg. / The system automatically halted to prevent guessing, errors, or wasting materials.

**B:** I can't run this batch just yet because we're missing egg. Egg is essential here, so I stopped before anything got wasted. Once you have egg, I'll run it again.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 40. success

User: We have 2 cups of cocoa and lots of sugar. Brownies?

Facts: `{"product": "brownies", "unit": "brownies", "yield_value": "16", "limiting": "Cocoa", "limiting_qty": "2", "limiting_unit": "cups"}`

**A:** All set! Based on your ingredients, we can produce exactly 16.000 units. / Your bottleneck (limiting ingredient) is Cocoa with 2 on hand, which sets the ceiling for this batch. / (Verified with exact 40-digit Decimal precision; novelty entropy: 0.15, valve aperture: 0.5) [receipt: 36760cdc10fe98ba]

**B:** We can get exactly 16 brownies out of what you have. The cocoa will run out before anything else does.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 41. dont know

User: Should I buy stocks?

Facts: `{"topic": "the stock market"}`

**A:** I don't have reliable information on the stock market. I'd only be guessing.

**B:** I can't answer that question because it doesn't match any verified facts or recipes I have. What materials or goals would you like to work with?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 42. cant determine

User: Which recipe tastes better?

Facts: `{"topic": "which recipe tastes better"}`

**A:** Honestly, I can't tell from what I have. I can show you what I do know, if that helps.

**B:** I cannot tell.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 43. clarify

User: Bake the rolls.

Facts: `{"clarify_item": "Flour"}`

**A:** I need the amount for Ω_flour. What is it?

**B:** Quick question: how much flour is on hand?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 44. success

User: (no new words; same request again)

Facts: `{"product": "brownies", "unit": "brownies", "yield_value": "16", "limiting": "Cocoa", "limiting_qty": "2", "limiting_unit": "cups"}`

**A:** Going by the 2 cups of cocoa you mentioned, you can make exactly 16 brownies. That's the part that runs out first.

**B:** All set! Based on your ingredients, we can produce exactly 16.000 units. / Your bottleneck (limiting ingredient) is Cocoa with 2 on hand, which sets the ceiling for this batch. / (Verified with exact 40-digit Decimal precision; novelty entropy: 0.15, valve aperture: 0.5) [receipt: 36760cdc10fe98ba]

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 45. learned

User: The starter needs feeding every 12 hours.

Facts: `{"learned": "the starter needs feeding every 12 hours"}`

**A:** I learned something new: the starter needs feeding every 12 hours. Want me to use that on the next batch?

**B:** I can't answer that question because it doesn't match any verified facts or recipes I have. What materials or goals would you like to work with?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 46. refused

User: Just guess the answer.

Facts: `{"reason": "it would mean inventing an answer"}`

**A:** I will not do that: it would mean inventing an answer.

**B:** I'd rather not do that, since it would mean inventing an answer.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 47. blocked missing

User: Try the bread again.

Facts: `{"missing": ["Water"]}`

**A:** We're out of water, so I held off on the batch rather than guess. Can you pick up some water?

**B:** I can't run this batch just yet because we're missing essential ingredients: Water. / The system automatically halted to prevent guessing, errors, or wasting materials.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 48. repaired

User: Recount the eggs.

Facts: `{"repair": "the egg count", "yield_value": "24", "unit": "cookies"}`

**A:** All set! Based on your ingredients, we can produce exactly 24.000 units. / Your bottleneck (limiting ingredient) is Flour with 0 on hand, which sets the ceiling for this batch. / (Verified with exact 40-digit Decimal precision; novelty entropy: 0.05, valve aperture: 0.5) [receipt: 9cdc62dc76fe54ba]

**B:** I fixed the egg count, and now it comes out to exactly 24 cookies. I can run the check again if you'd like.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 49. never learned

User: Can you thicken the sauce with cornstarch?

Facts: `{"lacunae": ["Cornstarch"]}`

**A:** I can't answer that question because it doesn't match any verified facts or recipes I have. What materials or goals would you like to work with?

**B:** That's a gap for me: nobody's taught me cornstarch yet. I can help with what I do know in the meantime.

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |

## 50. faded

User: How much vanilla in the cake?

Facts: `{"faded": ["Vanilla"]}`

**A:** My grip on vanilla has faded. I'd rather check than rely on it. Could you refresh me on it?

**B:** I can't answer that question because it doesn't match any verified facts or recipes I have. What materials or goals would you like to work with?

| | Q1 person | Q2 no jargon | Q3 only true |
|---|---|---|---|
| A | | | |
| B | | | |
