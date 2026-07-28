import sys
sys.path.insert(0, "/Users/Cridiv/Documents/Varve/service")
from services.datahub_service import resolve_dataset_financial_baseline, resolve_dataset_governance_multiplier

print("=== FINANCIAL BASELINE RESOLUTION ===")
urns = [
    "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.customers,PROD)",
    "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.products,PROD)",
    "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.countries,PROD)",
    "urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.promotions_v2,PROD)",
]
for m in urns:
    short = m.split(".")[-1].replace(",PROD)", "")
    res = resolve_dataset_financial_baseline(m)
    print(f"[{short}] Tier: {res['model_tier']} | Baseline: ${res['baseline_mrr']:,.2f} | Source: {res['baseline_source']}")
    if res["discrepancy_warning"]:
        print(f"  ⚠️ {res['discrepancy_warning']}")

print("\n=== GOVERNANCE MULTIPLIER CLAMPING ===")
gov = resolve_dataset_governance_multiplier("urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.customers,PROD)")
print(f"Multiplier: {gov['multiplier']}x | Clamped: {gov['is_multiplier_clamped']} | Reason: {gov['applied_reason']}")
