import xlrd
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from services.product_rule_categorizer_service import classify_product_name
from services.excel_price_service import clean_product_name

def analyze_with_ml():
    wb = xlrd.open_workbook(r'C:\Users\Administrator\Desktop\r.xls')
    sheet = wb.sheet_by_index(0)
    
    # 1. Collect all valid rows
    products = []
    for i in range(1, sheet.nrows):
        row = sheet.row_values(i)
        if len(row) >= 2:
            raw_name = str(row[1])
            if raw_name.strip():
                cleaned = clean_product_name(raw_name)
                products.append((raw_name, cleaned))
                
    # 2. Label data using Rule-Based Engine
    labeled_X = []
    labeled_y = []
    unlabeled_X = []
    unlabeled_raw = []
    
    for raw, cleaned in products:
        _, cat_name = classify_product_name(cleaned, {})
        if cat_name:
            labeled_X.append(cleaned)
            labeled_y.append(cat_name)
        else:
            unlabeled_X.append(cleaned)
            unlabeled_raw.append(raw)
            
    print(f"Total products: {len(products)}")
    print(f"Rule-based labeled: {len(labeled_X)}")
    print(f"Remaining uncategorized (to predict): {len(unlabeled_X)}")
    
    if not unlabeled_X:
        print("Nothing left to predict!")
        return

    # 3. Train ML Model on labeled data
    print("Training ML Model (TF-IDF + LinearSVC)...")
    model = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),
        ('clf', LinearSVC(random_state=42))
    ])
    model.fit(labeled_X, labeled_y)
    
    # 4. Predict unlabeled
    print("Predicting remaining categories...")
    predictions = model.predict(unlabeled_X)
    
    # 5. Summarize ML predictions
    ml_counts = defaultdict(int)
    ml_samples = defaultdict(list)
    
    for i in range(len(unlabeled_raw)):
        pred_cat = predictions[i]
        raw_name = unlabeled_raw[i]
        ml_counts[pred_cat] += 1
        if len(ml_samples[pred_cat]) < 5:
            ml_samples[pred_cat].append(raw_name)
            
    print("\n--- ML PREDICTIONS FOR PREVIOUSLY UNCATEGORIZED ITEMS ---")
    sorted_ml = sorted(ml_counts.items(), key=lambda x: x[1], reverse=True)
    for cat, count in sorted_ml:
        print(f"\n{cat} (Predicted for {count} unknown products):")
        for sample in ml_samples[cat]:
            print(f"  - {sample}")

analyze_with_ml()
