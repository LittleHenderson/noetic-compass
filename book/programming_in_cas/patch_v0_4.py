import os

input_file = r'C:\Users\wakil\OneDrive\Desktop\tksCAS\book\programming_in_cas\Programming_in_CAS_v0_4_MECH_AUDIT.md'

with open(input_file, 'r', encoding='utf-8-sig') as f:
    text = f.read()

replacements = {
    "Version: 0.2 (Audited)": "Version: 0.4 Draft / Mechanical Audit",
    
    "`StateCluster{^8^C, ^1^C, ^0^P} \\ StateCluster{^0^P, ^8^C}` *[compiler-valid via cas notation]*": "`StateCluster{^8^C, ^1^C, ^0^P} \\ StateCluster{^0^P, ^8^C}` *[conceptual]*",
    
    "**INVALID:** `^9_{F2}` *[compiler-invalid]*": "**DISCOURAGED:** `^9_{F2}` *[strict-mode warning]*",
    
    "**INVALID:** `CO-4^O + CO-4^E` *[compiler-invalid]*": "**DISCOURAGED:** `CO-4^O + CO-4^E` *[conceptual invalid]*",
    
    "If you attempt `^8^C * ^5^E` *[compiler-invalid]*, the compiler will throw": "If you attempt `^8^C * ^5^E` *[accepted but discouraged]*, the strict-mode compiler will throw",
    
    "If the math holds, the AI is certified. If the math fails, the AI is flagged for compliance review.": "If the math holds, the AI passes structural validation. If the math fails, the AI is flagged for compliance review."
}

for old, new in replacements.items():
    if old in text:
        text = text.replace(old, new)
        print(f"Replaced: {old[:20]}...")
    else:
        print(f"Warning: Not found: {old}")

with open(input_file, 'w', encoding='utf-8-sig') as f:
    f.write(text)

print('Success')
