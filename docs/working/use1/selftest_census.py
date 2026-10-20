"""Self-test on synthetic sentences (no source text): the key pair, the flags and the HTML stripper behave as built."""
import sys
sys.argv = ["x"]
sys.path.insert(0, r"C:\Users\wakil\Documents\Codex\2026-10-19\use1")
import census_c1 as C
cases = ["We have 3 eggs.", "I'm out of milk.", "We ran out of flour.", "I have a recipe that calls for 2 cups of flour.",
         "Take two cups of flour and mix.", "I made 3 loaves of bread.", "Do we have any milk left?"]
for s in cases:
    kp = C.SX.s_key_pair(s)
    print(kp["key"]["key"], C.flags(s), "would_ask=", C.MY.would_ask(s), "|", s)
b = C.body_text("<p>First para. Second sentence here.</p><pre><code>We have 3 eggs.</code></pre><blockquote>We have 2 eggs.</blockquote><p>We are out of salt today.</p>")
print(list(C.MY.sentences(b)))
