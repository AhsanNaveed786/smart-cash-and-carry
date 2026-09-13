import xlrd
from collections import defaultdict
from services.product_rule_categorizer_service import classify_product_name
from services.excel_price_service import clean_product_name

def analyze():
    wb = xlrd.open_workbook(r'C:\Users\Administrator\Desktop\r.xls')
    sheet = wb.sheet_by_index(0)
    
    category_counts = defaultdict(int)
    category_samples = defaultdict(list)
    
    # Skip header
    for i in range(1, sheet.nrows):
        row = sheet.row_values(i)
        if len(row) < 2:
            continue
            
        raw_name = str(row[1])
        if not raw_name.strip():
            continue
            
        # Clean the name just like the upload does
        cleaned_name = clean_product_name(raw_name)
        
        # Use our rule engine
        cat_id, cat_name = classify_product_name(cleaned_name, {})
        category = cat_name if cat_name else "Uncategorized"
        
        category_counts[category] += 1
        if len(category_samples[category]) < 5:
            category_samples[category].append(raw_name)
            
    print("--- CATEGORIZATION SUMMARY ---")
    # Sort by count descending
    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    
    for cat, count in sorted_categories:
        print(f"\n{cat} ({count} products):")
        for sample in category_samples[cat]:
            print(f"  - {sample}")

analyze()
