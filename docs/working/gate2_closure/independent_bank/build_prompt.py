"""
Track A — Build the elicitation prompt for an AI authoring model.

Reads cell_descriptions_colloquial.json and produces a ready-to-use prompt
string for a frontier AI model. The prompt contains ONLY colloquial English
descriptions — zero TKS/CAS terminology.

Usage:
    python build_prompt.py [--items-per-cell 10] [--output prompt.txt]
"""
import json, argparse


def build_prompt(cell_file: str, items_per_cell: int = 10) -> str:
    with open(cell_file, encoding="utf-8") as f:
        data = json.load(f)
    
    cells = data["cells"]
    worlds = data["worlds"]
    
    # Build per-world cell descriptions
    sections = {}
    for w in ["A", "B", "C", "D"]:
        world = worlds[w]
        lines = []
        lines.append(f"### {world['name_plain']}")
        lines.append(world["description_plain"])
        lines.append("")
        
        for n in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]:
            code = f"{w}{n}"
            cell = cells[code]
            lines.append(f"**{code} — {cell['label_plain']}**")
            lines.append(cell["description_plain"])
            lines.append("")
            lines.append("Examples of this category (what to write about):")
            for ex in cell["examples_positive"]:
                lines.append(f"- {ex}")
            lines.append("")
            lines.append("Not this category (what to avoid):")
            for ex in cell["examples_negative"]:
                lines.append(f"- {ex}")
            lines.append("")
        
        sections[w] = "\n".join(lines)
    
    # Read the template
    with open("elicit_prompt_template.txt", encoding="utf-8") as f:
        template = f.read()
    
    total = items_per_cell * 40
    prompt = template.format(
        cell_descriptions_A=sections["A"],
        cell_descriptions_B=sections["B"],
        cell_descriptions_C=sections["C"],
        cell_descriptions_D=sections["D"],
        items_per_cell=items_per_cell,
        total_items=total
    )
    
    return prompt


def main():
    parser = argparse.ArgumentParser(description="Build AI elicitation prompt")
    parser.add_argument("--cell-file", default="cell_descriptions_colloquial.json",
                        help="Cell descriptions JSON")
    parser.add_argument("--items-per-cell", type=int, default=10,
                        help="Target items per cell")
    parser.add_argument("--output", default="elicit_prompt.txt",
                        help="Output prompt file")
    args = parser.parse_args()
    
    prompt = build_prompt(args.cell_file, args.items_per_cell)
    
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(prompt)
    
    # Count TKS terms (should be zero)
    tks_terms = ["noetic", "cognitive operator", "co-^", "^0", "^1", "^2", "^3", "^4",
                 "^5", "^6", "^7", "^8", "^9", "cognitive architecture system",
                 "tootra", "involution", "processing domain", "phenomenological register",
                 "cas register", "|t", "|a",
                 "nccs", "noetic compass", "cas harness", "rpm monad"]
    prompt_lower = prompt.lower()
    hits = [t for t in tks_terms if t.lower() in prompt_lower]
    
    print(f"Prompt written to {args.output}")
    print(f"Length: {len(prompt):,} chars")
    print(f"TKS terminology check: ", end="")
    if hits:
        print(f"FAIL — found: {hits}")
    else:
        print("PASS — zero TKS terms detected")
    
    # Check that every cell code appears
    for w in "ABCD":
        for n in ["1","2","3","4","5","6","7","8","9","10"]:
            code = f"{w}{n}"
            if f"**{code}" not in prompt:
                print(f"WARNING: cell {code} not found in prompt")


if __name__ == "__main__":
    main()
