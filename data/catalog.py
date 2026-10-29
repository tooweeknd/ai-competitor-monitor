"""Synthetic demo catalog: consumer-health categories (oral care, digestive,
pain relief, vitamins, nasal care) across quick commerce, marketplace and
e-pharma platforms in India. All prices, availability and ratings are invented
for demonstration. Brand names are public trademarks of their owners."""

BRAND_OWNER = {
    "Sensodyne": "Haleon", "Eno": "Haleon", "Crocin": "Haleon",
    "Centrum": "Haleon", "Otrivin": "Haleon",
    "Colgate Total": "Colgate-Palmolive", "Pepsodent": "Hindustan Unilever",
    "Digene": "Abbott", "Gaviscon": "Reckitt",
    "Dolo-650": "Micro Labs", "Combiflam": "Sanofi",
    "Supradyn": "Bayer", "HealthKart HK Vitals": "HealthKart",
    "Nasivion": "Merck", "Vicks VapoInhaler": "P&G",
}

FOCUS_OWNER = "Haleon"   # the "house" brands the monitor is tuned to watch

SKUS = [
    # sku_id, brand, category, variant, pack
    ("ORC-SEN-FM75",  "Sensodyne", "Oral Care", "Fresh Mint 75g", 1),
    ("ORC-SEN-RP100", "Sensodyne", "Oral Care", "Repair & Protect 100g", 1),
    ("ORC-COL-TT200", "Colgate Total", "Oral Care", "Total 200g (twin pack)", 2),
    ("ORC-PEP-GC150", "Pepsodent", "Oral Care", "Germicheck 150g", 1),
    ("DIG-ENO-LE6",   "Eno", "Digestive Health", "Lemon 6 sachets", 1),
    ("DIG-ENO-OR30",  "Eno", "Digestive Health", "Orange 30 sachets", 1),
    ("DIG-DGN-MI200", "Digene", "Digestive Health", "Mint liquid 200ml", 1),
    ("DIG-GAV-AN150", "Gaviscon", "Digestive Health", "Aniseed liquid 150ml", 1),
    ("PAI-CRO-500T15","Crocin", "Pain Relief", "500mg 15 tabs", 1),
    ("PAI-CRO-ADV20", "Crocin", "Pain Relief", "Advance 20 tabs", 1),
    ("PAI-DOL-650T15","Dolo-650", "Pain Relief", "650mg 15 tabs", 1),
    ("PAI-CBF-T10",   "Combiflam", "Pain Relief", "10 tabs", 1),
    ("VIT-CEN-A30",   "Centrum", "Vitamins & Supplements", "Adults 30 tabs", 1),
    ("VIT-CEN-W50",   "Centrum", "Vitamins & Supplements", "Women 50 tabs", 1),
    ("VIT-SUP-D60",   "Supradyn", "Vitamins & Supplements", "Daily 60 tabs", 1),
    ("VIT-HKV-M60",   "HealthKart HK Vitals", "Vitamins & Supplements", "Multivitamin 60 tabs", 1),
    ("NAS-OTR-AD10",  "Otrivin", "Nasal Care", "Adult 10ml", 1),
    ("NAS-NSV-PE10",  "Nasivion", "Nasal Care", "Paediatric 10ml", 1),
    ("NAS-VIC-IN1",   "Vicks VapoInhaler", "Nasal Care", "Inhaler single", 1),
]

PLATFORMS = [
    # platform, kind
    ("Blinkit", "Quick commerce"),
    ("Zepto", "Quick commerce"),
    ("Swiggy Instamart", "Quick commerce"),
    ("Amazon", "Marketplace"),
    ("Flipkart Minutes", "Quick commerce"),
    ("1mg", "E-pharmacy"),
    ("PharmEasy", "E-pharmacy"),
]

LOCATIONS = [
    ("Gurgaon", "122001"), ("Gurgaon", "122018"),
    ("Delhi", "110016"), ("Delhi", "110085"),
    ("Mumbai", "400050"), ("Mumbai", "400076"),
    ("Bengaluru", "560034"), ("Bengaluru", "560066"),
]

# Base MRPs are invented demo numbers, not live market prices.
BASE_MRP = {
    "ORC-SEN-FM75": 210, "ORC-SEN-RP100": 320, "ORC-COL-TT200": 185,
    "ORC-PEP-GC150": 99, "DIG-ENO-LE6": 55, "DIG-ENO-OR30": 250,
    "DIG-DGN-MI200": 120, "DIG-GAV-AN150": 240, "PAI-CRO-500T15": 50,
    "PAI-CRO-ADV20": 45, "PAI-DOL-650T15": 33, "PAI-CBF-T10": 42,
    "VIT-CEN-A30": 475, "VIT-CEN-W50": 620, "VIT-SUP-D60": 425,
    "VIT-HKV-M60": 649, "NAS-OTR-AD10": 99, "NAS-NSV-PE10": 89,
    "NAS-VIC-IN1": 165,
}
