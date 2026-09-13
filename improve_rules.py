with open(r'd:\Projects\smart-cash-and-carry\services\product_rule_categorizer_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = {
    r'r"\bwater(?!\s+(gun|bottle|cooler|dispenser))\b"': r'r"\bwater(?!\s+(gun|bottle|cooler|dispenser|set|glass|jug|filter))\b"',
    r'r"\begg\b"': r'r"\begg(?!\s+(beater|cutter|slicer|tray|boiler))\b"',
    r'r"\beggs\b"': r'r"\beggs(?!\s+(beater|cutter|slicer|tray|boiler))\b"',
    r'r"\bvegetable\b"': r'r"\bvegetable(?!\s+(rack|cutter|chopper|slicer))\b"',
    r'r"\bpotato\b"': r'r"\bpotato(?!\s+(masher|peeler|cutter))\b"',
    r'r"\baloo\b"': r'r"\baloo(?!\s+(samosa|roll|paratha))\b"',
    r'r"\bbread\b"': r'r"\bbread(?!\s+(box|knife|maker))\b"',
    r'r"\bcake\b"': r'r"\bcake(?!\s+(pan|set|stand|base))\b"',
    r'r"\bgum\b"': r'r"\bgum(?!\s+(uhu|stick|nail))\b"',
    r'r"\bpen\b"': r'r"\bpen(?!\s+(candel|drive))\b"',
    r'r"\bpencil\b"': r'r"\bpencil(?!\s+(lip|eye))\b"',
    r'r"\bcolor\b"': r'r"\bcolor(?!\s+(hair|smog))\b"',
    r'r"\bmeat\b"': r'r"\bmeat(?!\s+(hammer|hamer|mincer|tenderizer))\b"',
    r'r"\bchicken\b"': r'r"\bchicken(?!\s+(karahi|masala|powder))\b"',
    r'r"\bcar\b"': r'r"\bcar(?!\s+(charger|perfume|air|freshener))\b"',
}

for old, new in replacements.items():
    content = content.replace(old, new)

content = content.replace(r'"Personal Care": [', r'"Personal Care": [\n        r"\blip\s*stick\b", r"\blip\s*pencil\b", r"\beye\s*pencil\b", r"\bnail\s*gum\b", r"\btissue\s*box\b",')

with open(r'd:\Projects\smart-cash-and-carry\services\product_rule_categorizer_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Rules improved!")
