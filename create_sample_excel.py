import pandas as pd

data = {
    'Category': ['Flooring', 'Painting', 'Carpentry', 'Plumbing'],
    'Description': ['Vinyl Flooring 5mm', 'Whole House Painting (3 Room)', 'Kitchen Cabinet (Top & Bottom)', 'Install Kitchen Sink'],
    'Unit': ['sqft', 'LS', 'ft', 'no'],
    'Unit Price': [5.50, 1500.00, 120.00, 80.00],
    'Code': ['VF001', 'PNT001', 'KC001', 'PLB001']
}

df = pd.DataFrame(data)
df.to_excel('sample_prices.xlsx', index=False)
print("Created sample_prices.xlsx")
