"""build_phrasebook.py -- writes <repo>/phrasebook.json for helm_voice.py.

The phrasings below are hand-written, seeded from three sources and tagged with where each came from:
  roadmap:<row>      HELM_CAPABILITIES_ROADMAP_AND_DEVELOPMENTAL_STAGES.md section 2.6, right-hand column
  how_it_talks:#N    docs/working/noetic_council/language_v3/HOW_IT_TALKS.txt example N (the 15 examples)
  cce:<form>         the fixed surface forms in language_v3/cce.py (UNDETERMINED / REFUSE / CLARIFY / ...)
  sdg:<frame>        a phrase frame mined from the 5,268-row SDG English corpus (SDG_PHRASE_MINING.json);
                     the builder attaches the first three seed_ids where that frame occurs
  new                written fresh for this phrasebook

Every phrasing carries a Register: f warm (default), A analytical (asked for detail), E hands-on, T big-picture.
Placeholders (helm_voice fills them only from the receipt or the conversation memory):
  {yield_q} {unit} {product} {limiting} {Limiting} {lim_have} {missing} {Missing} {missing_verb} {missing_pron}
  {item} {topic} {reason} {learned} {repair} {Repair} {gaps} {Gaps} {gaps_verb} {gaps_pron} {user_have}
needs: extra conditions from memory -- "user_said" (the user's own words name the limiting amount and they match
the receipt), "same_limiting" (last answer had the same limiting ingredient), "same_missing".

Usage:  python -X utf8 -B build_phrasebook.py      (reads SDG_PHRASE_MINING.json next to this file)
"""
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

P = []  # (situation, register, text, sources, needs)


def add(sit, reg, text, src=("new",), needs=()):
    P.append((sit, reg, text, list(src), list(needs)))


# ---------------------------------------------------------------- success (ANSWER with a yield)
S = "success"
add(S, "f", "Good news: you can make {yield_q} {unit} of {product}. {Limiting} is what runs out first, so that's what caps this batch.", ["roadmap:recipe_production"])
add(S, "f", "You're good to go! That works out to {yield_q} {unit}, and {limiting} sets the ceiling.", ["roadmap:recipe_production"])
add(S, "f", "We can get {yield_q} {unit} out of what you have. The {limiting} will run out before anything else does.")
add(S, "f", "Looks like {yield_q} {unit} of {product} is doable. {Limiting} is the bottleneck here, with {lim_have} on hand.", ["roadmap:recipe_production"])
add(S, "f", "You'll get {yield_q} {unit} this way. If you want more, {limiting} is the thing to pick up.")
add(S, "A", "The batch comes to {yield_q} {unit}. {Limiting} is the limiting ingredient: it runs out first, so it sets the maximum.", ["roadmap:recipe_production"])
add(S, "A", "With the amounts given, the most you can make is {yield_q} {unit}. The cap comes from {limiting}, with {lim_have} on hand.", ["roadmap:recipe_production"])
add(S, "A", "These inputs together yield {yield_q} {unit}. {Limiting} is the first to run out, so it decides the total.", ["sdg:these_inputs_together_yield"])
add(S, "E", "To produce {product}, combine what you have and you'll get {yield_q} {unit}. The {limiting} is the first thing to run out.", ["sdg:open_to_produce", "sdg:combine_with"])
add(S, "E", "Get the {limiting} out first; it's the part that runs out, and it'll carry you to {yield_q} {unit}.")
add(S, "T", "Overall, what you have adds up to {yield_q} {unit} of {product}. Together these ingredients produce that much, and {limiting} is what holds the total back.", ["sdg:together_these_produce"])
add(S, "T", "Big picture: {limiting} decides how far this goes, and right now that comes to {yield_q} {unit}.")
add(S, "f", "You said you had {user_have}, and that's what runs out first. It's enough for {yield_q} {unit}.", ["new"], ["user_said"])
add(S, "f", "Going by the {user_have} you mentioned, you can make {yield_q} {unit}. That's the part that runs out first.", ["new"], ["user_said"])
add(S, "A", "You said you had {user_have}; that is the limiting amount, and it gives {yield_q} {unit}.", ["new"], ["user_said"])
add(S, "f", "{Limiting} is the bottleneck again. This time you can make {yield_q} {unit}.", ["new"], ["same_limiting"])
add(S, "f", "Same story with the {limiting}: it runs out first, and it caps you at {yield_q} {unit}.", ["new"], ["same_limiting"])
add(S, "A", "{Limiting} is still the limiting ingredient; it caps this run at {yield_q} {unit}.", ["new"], ["same_limiting"])

# ---------------------------------------------------------------- blocked_missing (REFUSE: a required input is absent)
S = "blocked_missing"
add(S, "f", "I can't run this batch just yet because we're missing {missing}. {Missing} {missing_verb} essential here, so I stopped before anything got wasted.", ["roadmap:missing_prerequisite"])
add(S, "f", "Hold on, there's no {missing} on hand, and this recipe can't go ahead without {missing_pron}.", ["how_it_talks:#11", "roadmap:missing_prerequisite"])
add(S, "f", "We're out of {missing}, so I held off on the batch rather than guess.")
add(S, "f", "I stopped here: the recipe needs {missing}, and we don't have any right now.", ["how_it_talks:#10"])
add(S, "A", "The batch is blocked: {missing} {missing_verb} required, and the amount on hand is zero. I halted instead of filling in a guess.", ["how_it_talks:#11"])
add(S, "A", "I can't work out an amount yet. {Missing} {missing_verb} a required input, and none is recorded.", ["roadmap:missing_prerequisite"])
add(S, "E", "Before we start, you'll need {missing}; without {missing_pron} this recipe won't come together.", ["how_it_talks:#10"])
add(S, "E", "Grab some {missing} first. I can't make this batch without {missing_pron}.")
add(S, "T", "{Missing} {missing_verb} a must-have for this recipe, and right now we don't have {missing_pron}. I'd rather wait than fake it.")
add(S, "T", "Everything else can wait: the batch depends on {missing}, and we're missing {missing_pron}.")
add(S, "f", "Still no {missing}, so I'm holding off again.", ["new"], ["same_missing"])
add(S, "f", "We're still missing {missing}, so the batch has to wait.", ["new"], ["same_missing"])

# ---------------------------------------------------------------- cant_determine (UNDETERMINED)
S = "cant_determine"
add(S, "f", "Honestly, I can't tell from what I have.", ["how_it_talks:#13", "cce:FIXED_UNDETERMINED"])
add(S, "f", "I'm not sure, and I'd rather say so than guess.", ["how_it_talks:#13"])
add(S, "f", "I can't call this one yet; with what I know, it could go either way.")
add(S, "f", "I don't have enough to settle {topic}, so I won't pretend I do.")
add(S, "A", "This comes out undecided: the facts I have fit more than one answer, so I can't pick one.", ["cce:FIXED_UNDETERMINED"])
add(S, "A", "I can't tell {topic} from the recorded facts; more than one answer is still possible.")
add(S, "E", "I can't tell yet. Give me one more measurement and I'll try again.")
add(S, "E", "Not sure on this one. Let's check it again once we know a bit more.")
add(S, "T", "Stepping back, {topic} isn't settled by what I know, so I'll leave it open.")
add(S, "T", "The bigger picture isn't clear enough yet for me to say.")

# ---------------------------------------------------------------- dont_know (CLARIFY with nothing to ground it)
S = "dont_know"
add(S, "f", "I can't answer that because there are no verified facts connecting those ideas in what I know.", ["roadmap:ungrounded_question"])
add(S, "f", "I don't know {topic}, and I won't guess without real information.")
add(S, "f", "That's outside what I know, so I'd rather not make something up.")
add(S, "f", "I don't have reliable information on {topic}. I'd only be guessing.")
add(S, "A", "There are no verified facts on {topic} in my records, so any answer would be invented.", ["roadmap:ungrounded_question"])
add(S, "A", "Nothing I have covers this, so I can't support an answer.", ["how_it_talks:#8", "cce:REFUSE_CLAIM"])
add(S, "E", "I don't know that one. If you can show me where the facts come from, I'll work with them.")
add(S, "E", "No solid facts on that here, so I can't give you a real answer.")
add(S, "T", "That's beyond what I've got facts for, so I'll stay quiet rather than guess.")
add(S, "T", "I don't have any grounding for {topic}, and I don't fill gaps with made-up answers.")

# ---------------------------------------------------------------- clarify (CLARIFY: one amount is needed)
S = "clarify"
add(S, "f", "How much {item} do you have? I need that before I can work this out.", ["how_it_talks:#9", "cce:CLARIFY"])
add(S, "f", "Quick question: how much {item} is on hand?", ["how_it_talks:#9"])
add(S, "f", "I just need one number: how much {item} do we have?")
add(S, "f", "Can you tell me how much {item} there is? Then I can figure out the rest.")
add(S, "A", "I need the amount of {item} to finish the calculation. What is it?", ["how_it_talks:#9", "cce:CLARIFY"])
add(S, "A", "One input is unknown: the amount of {item}. How much is there?")
add(S, "E", "Check your {item} for me: how much is there?")
add(S, "E", "Could you measure the {item} and tell me how much you've got?")
add(S, "T", "Before I go further, I need to know how much {item} we're working with. How much is it?")
add(S, "T", "Everything hinges on the {item}. How much do you have?")

# ---------------------------------------------------------------- refused (REFUSE: a boundary)
S = "refused"
add(S, "f", "I won't do that, because {reason}.", ["how_it_talks:#6", "cce:REFUSE"])
add(S, "f", "I'm not going to do that one: {reason}.", ["how_it_talks:#6"])
add(S, "f", "Sorry, I won't help with that, since {reason}.")
add(S, "f", "I'd rather not do that, since {reason}.")
add(S, "A", "I'm declining this request because {reason}.", ["cce:REFUSE"])
add(S, "A", "I won't proceed, since {reason}.")
add(S, "E", "I'm going to stop here and not do that, because {reason}.")
add(S, "E", "Not doing that one: {reason}.")
add(S, "T", "That goes against how I work: {reason}. So I won't do it.")
add(S, "T", "Some things I won't do, and this is one of them, because {reason}.")

# ---------------------------------------------------------------- learned (ANSWER: a teaching step was admitted)
S = "learned"
add(S, "f", "I learned something new: {learned}.")
add(S, "f", "Got it, now I know {learned}.")
add(S, "f", "Thanks, that taught me something: {learned}.")
add(S, "f", "Noted. I've updated my notes: {learned}.")
add(S, "A", "I've updated what I know: {learned}.")
add(S, "A", "New fact stored: {learned}.")
add(S, "E", "Okay, got it: {learned}.")
add(S, "E", "Lesson learned: {learned}.")
add(S, "T", "That's a useful lesson, and I've learned it: {learned}.")
add(S, "T", "I learned something that matters here: {learned}.")

# ---------------------------------------------------------------- repaired (ANSWER after a repair)
S = "repaired"
add(S, "f", "I caught a mistake in {repair} and fixed it.")
add(S, "f", "Quick correction: I had {repair} wrong, and I've put it right.")
add(S, "f", "I fixed {repair}; it checks out now.")
add(S, "f", "{Repair} was off, and I've corrected it.")
add(S, "A", "Repair done: {repair} was wrong; I corrected it and checked it again.")
add(S, "A", "I found an error in {repair}, corrected it, and re-checked the result.")
add(S, "E", "I went back over {repair}, found the slip, and fixed it.")
add(S, "T", "One thing was off, {repair}, and it's been put right.")
add(S, "f", "I fixed {repair}, and now it comes out to {yield_q} {unit}.")
add(S, "f", "After correcting {repair}, the answer is {yield_q} {unit}.")
add(S, "A", "I corrected {repair}. With that fixed, the result comes to {yield_q} {unit}.")
add(S, "E", "I fixed {repair}, and that gets you {yield_q} {unit}.")
add(S, "T", "With {repair} put right, the total comes to {yield_q} {unit}.")

# ---------------------------------------------------------------- never_learned (lacuna: never charged)
S = "never_learned"
add(S, "f", "I've never been taught {gaps}, so I can't speak to {gaps_pron}.")
add(S, "f", "That's a gap for me: nobody's taught me {gaps} yet.")
add(S, "f", "I haven't been taught {gaps}, so I won't guess.")
add(S, "f", "{Gaps} {gaps_verb} new to me; I've never been taught {gaps_pron}.")
add(S, "A", "No record: {gaps} {gaps_verb} something I was never taught, so there's nothing to draw on.")
add(S, "A", "I was never taught {gaps}. This is a true gap, not something I forgot.")
add(S, "E", "I've never been taught {gaps}. Show me once and I'll have something to go on.")
add(S, "E", "I haven't been taught {gaps} yet, so I can't walk you through {gaps_pron}.")
add(S, "T", "{Gaps} {gaps_verb} outside anything I've been taught so far.")
add(S, "T", "There's a hole in what I know: I was never taught {gaps}.")

# ---------------------------------------------------------------- faded (charged before, below the floor now)
S = "faded"
add(S, "f", "I used to know {gaps}, but that's faded, so I don't trust my answer anymore.")
add(S, "f", "I learned {gaps} before, but it's slipped, and I'd want a refresher.")
add(S, "f", "My grip on {gaps} has faded. I'd rather check than rely on {gaps_pron}.")
add(S, "f", "{Gaps} used to be solid for me, but I can't rely on that anymore.")
add(S, "A", "I was taught {gaps} earlier, but it no longer checks out. That's knowledge that faded, not something I lacked.")
add(S, "A", "Earlier I had {gaps} right; now I don't, so that knowledge has faded.")
add(S, "E", "I'm rusty on {gaps}. Walk me through {gaps_pron} once more and I'll get back on track.")
add(S, "E", "I used to have {gaps} down, but I've lost my grip on {gaps_pron}.")
add(S, "T", "Something I once knew, {gaps}, has faded over time.")
add(S, "T", "{Gaps} slipped away from me, so I'd treat my old answer with care.")

# ---------------------------------------------------------------- dialogue-act tails: question back / offer
TAILS = {
    "success": {"question": ["Is that enough for what you need?", "Is that the batch size you were hoping for?",
                             "Do you have any more {limiting} around?"],
                "offer": ["I can work out how much more {limiting} you'd need for a bigger batch, if you like.",
                          "Want me to show you the numbers behind this?", "I can check other ingredient amounts too, if that helps."]},
    "blocked_missing": {"question": ["Do you have any {missing} somewhere?", "Can you pick up some {missing}?",
                                     "Is there any {missing} tucked away somewhere?"],
                        "offer": ["Once you have {missing}, I'll run it again.",
                                  "I can tell you how much {missing} the recipe calls for, if you want.",
                                  "Tell me when you've got {missing_pron} and I'll take it from there."]},
    "cant_determine": {"question": ["Can you tell me a bit more?", "Do you have another measurement I could use?",
                                    "What else do you know about it?"],
                       "offer": ["If you give me one more fact, I'll take another look.",
                                 "I can show you what I do know, if that helps.",
                                 "I can list what's still unclear, if you want."]},
    "dont_know": {"question": ["Is there something related I can help with?", "What problem are you trying to solve?",
                               "Do you have a source you'd like me to work from?"],
                  "offer": ["If you share the facts, I'll work with them.",
                            "I'm happy to help with something I do have facts for.",
                            "Give me the details and I'll take a look."]},
    "clarify": {"question": ["Do you know it offhand?", "Is it handy?", "Can you check?"],
                "offer": ["Then I'll do the math.", "Once I have it, the rest is quick.",
                          "After that I can finish the calculation."]},
    "refused": {"question": ["Is there another way I can help?", "Want to try a different approach?",
                             "What were you hoping to get done?"],
                "offer": ["I'm glad to help with something else.", "I can explain my reasons, if that's useful.",
                          "Let me know what else you need."]},
    "learned": {"question": ["Is there anything else I should know?", "Did I get that right?",
                             "Want me to use that on the next batch?"],
                "offer": ["I can redo the last calculation with it, if you want.", "I can show you what changed.",
                          "Tell me if there's more to it."]},
    "repaired": {"question": ["Does that match what you expected?", "Want me to walk through the fix?",
                              "Should I double-check anything else?"],
                 "offer": ["I can show you exactly what changed.", "I can run the check again if you'd like.",
                           "Happy to walk through it step by step."]},
    "never_learned": {"question": ["Could you show me how it works?", "Do you have an example I could study?",
                                   "Want to teach me?"],
                      "offer": ["If you teach me, I'll add it to what I know.", "Give me an example and I'll study it.",
                                "I can help with what I do know in the meantime."]},
    "faded": {"question": ["Could you refresh me on it?", "Want to go over it together?",
                           "Do you have the details handy?"],
              "offer": ["If you remind me, I'll go over it again.", "I can check what I still have on it.",
                        "Let's go over it again and I'll get it back."]},
}

# ---------------------------------------------------------------- plain templates (the guard's fallback; two each)
PLAIN = {
    "success": ["You can make {yield_q} {unit}. {Limiting} runs out first.",
                "The total is {yield_q} {unit}, and {limiting} runs out first."],
    "blocked_missing": ["I can't make this yet because {missing} {missing_verb} missing.",
                        "This has to wait: {missing} {missing_verb} missing."],
    "cant_determine": ["I can't tell.", "I can't tell yet from what I have."],
    "dont_know": ["I don't have verified facts on that, so I won't guess.",
                  "I don't know that, and I won't guess."],
    "clarify": ["How much {item} is there?", "What is the amount of {item}?"],
    "refused": ["I won't do that, because {reason}.", "I'm not going to do that, because {reason}."],
    "learned": ["I learned that {learned}.", "I've learned this: {learned}."],
    "repaired": ["I fixed {repair}.", "I corrected {repair}."],
    "repaired+yield": ["I fixed {repair}, and the result is {yield_q} {unit}.",
                       "I corrected {repair}; the result is {yield_q} {unit}."],
    "never_learned": ["I was never taught {gaps}.", "I've never been taught {gaps}."],
    "faded": ["I used to know {gaps}, but it has faded.", "My knowledge of {gaps} has faded."],
}

SITUATIONS = ["success", "blocked_missing", "cant_determine", "dont_know", "clarify", "refused", "learned",
              "repaired", "never_learned", "faded"]


def main():
    mining_path = os.path.join(HERE, "SDG_PHRASE_MINING.json")
    with open(mining_path, encoding="utf-8") as f:
        mining = json.load(f)
    with open(mining_path, "rb") as f:
        mining_sha = hashlib.sha256(f.read()).hexdigest()
    entries, counters, cited = [], {}, set()
    for sit, reg, text, src, needs in P:
        assert sit in SITUATIONS and reg in "fAET", (sit, reg)
        counters[(sit, reg)] = counters.get((sit, reg), 0) + 1
        pid = "%s.%s.%02d" % (sit, reg, counters[(sit, reg)])
        cites = []
        for s in src:
            if s.startswith("sdg:"):
                fr = mining["frames"][s[4:]]
                assert fr["count"] > 0, s
                cites += fr["seed_ids"][:3]
        cited.update(cites)
        entries.append({"id": pid, "situation": sit, "register": reg, "text": text, "sources": src,
                        "sdg_seed_ids": cites, "needs": needs})
    tails = []
    for sit, acts in TAILS.items():
        for act, lst in acts.items():
            for i, t in enumerate(lst, 1):
                tails.append({"id": "%s.%s.%02d" % (sit, act, i), "situation": sit, "act": act, "text": t})
    per = {s: sum(1 for e in entries if e["situation"] == s) for s in SITUATIONS}
    book = {
        "schema": "helm.voice.phrasebook/1",
        "built_by": "docs/working/voice_20261018/build_phrasebook.py",
        "sources": {
            "roadmap": "HELM_CAPABILITIES_ROADMAP_AND_DEVELOPMENTAL_STAGES.md section 2.6 (lines 230-266), right-hand column",
            "how_it_talks": "docs/working/noetic_council/language_v3/HOW_IT_TALKS.txt (15 examples)",
            "cce": "docs/working/noetic_council/language_v3/cce.py fixed surface forms",
            "sdg": {"mining_file": "docs/working/voice_20261018/SDG_PHRASE_MINING.json", "mining_sha256": mining_sha,
                    "corpus_files_sha256": mining["files_sha256"], "rows_streamed": mining["rows_streamed"],
                    "seed_ids_cited": sorted(cited)},
        },
        "registers": {"f": "warm (default for a normal user)", "A": "analytical (when the user asks for detail)",
                      "E": "hands-on", "T": "big-picture"},
        "situations": SITUATIONS,
        "counts": {"phrasings": len(entries), "per_situation": per, "tails": len(tails)},
        "entries": entries,
        "tails": tails,
        "plain": PLAIN,
    }
    dst = os.path.join(REPO, "phrasebook.json")
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        json.dump(book, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("phrasebook:", len(entries), "phrasings,", len(tails), "tails ->", dst)
    print("per situation:", per)
    print("sdg seed_ids cited:", len(cited))


if __name__ == "__main__":
    main()
