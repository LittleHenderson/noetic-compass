import io
import re

SRC = r"C:\Users\wakil\OneDrive\Desktop\tksCAS\book\CAS_Component_Companion\CAS_Component_Mathematics.html"
s = io.open(SRC, encoding="utf-8").read()

print("style open blocks:", len(re.findall(r"<style", s)))
print("style close:", len(re.findall(r"</style>", s)))
print("has <body>:", "<body" in s, "| has <html>:", "<html" in s, "| has </head>:", "</head>" in s)

i = s.index("</style>")
print("\n--- 400 chars after first </style> ---")
print(repr(s[i:i + 400]))

print("\n--- last 300 chars ---")
print(repr(s[-300:]))

print("\n--- marker counts ---")
for k in ["class=\"part", "class=\"circuit", "class=\"fam", "<figure",
          "class=\"guards", "class=\"row2", "class=\"boundary",
          "class=\"colophon", "class=\"grade-row", "class=\"verbs",
          "class=\"ex", "<section", "<h1", "<h2", "<h3", "<svg"]:
    print(f"  {k:24} {s.count(k)}")
