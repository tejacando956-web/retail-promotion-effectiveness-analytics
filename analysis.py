"""Promotion effectiveness analysis.

For every campaign we compare the promotion window with a *matched baseline*:
the 28 days immediately before the campaign for the same category, using only
'clean' days (no promotion and not in a post-promo dip week) so the baseline
is not contaminated by other campaigns or pull-forward effects.

Metrics per campaign / discount bucket:
  uplift_pct            promo daily units per SKU-store vs baseline, %
  incremental_units     (promo daily rate - baseline daily rate) x promo exposure
  incremental_revenue   same logic applied to daily revenue
  incremental_gross_profit  promo gross profit - expected baseline gross profit
  discount_cost         units sold on promo x base price x discount %
  promo_roi             incremental gross profit / discount cost
  margin_pct_promo / margin_pct_baseline
  post_promo_dip_pct    fall in daily units in the 7 days after the promo vs baseline, %
Run: python3 analysis.py  (after generate_data.py)
"""
import numpy as np
import pandas as pd

BASELINE_DAYS = 28
DIP_DAYS = 7

def main():
    products = pd.read_csv("data/products.csv")
    promos = pd.read_csv("data/promotions.csv", parse_dates=["start_date", "end_date"])
    sales = pd.read_csv("data/sales.csv", parse_dates=["date"])
    sales = sales.merge(products[["sku_id", "category", "base_price", "unit_cost"]], on="sku_id", how="left")
    sales["gross_profit"] = sales["revenue"] - sales["units"] * sales["unit_cost"]
    sales["discount_cost"] = sales["units"] * sales["base_price"] * sales["discount_pct_applied"] / 100.0

    # mark dip days: the 7 days after any campaign ends, for that category
    dip_keys = set()
    for _, pr in promos.iterrows():
        for d in pd.date_range(pr["end_date"] + pd.Timedelta(days=1),
                               pr["end_date"] + pd.Timedelta(days=DIP_DAYS)):
            dip_keys.add((pr["scope_value"], d))
    sales["is_promo"] = sales["promo_id"].notna()
    sales["is_dip"] = [ (c, d) in dip_keys and not p for c, d, p in zip(sales["category"], sales["date"], sales["is_promo"]) ]
    sales["is_clean"] = ~sales["is_promo"] & ~sales["is_dip"]

    def window_stats(cat, start, end, clean_only=False):
        m = (sales["category"] == cat) & (sales["date"] >= start) & (sales["date"] <= end)
        if clean_only:
            m &= sales["is_clean"]
        w = sales[m]
        exposure = w[["date", "sku_id", "store_id"]].drop_duplicates().shape[0]
        if exposure == 0:
            return None
        return {
            "daily_units": w["units"].sum() / exposure,
            "daily_revenue": w["revenue"].sum() / exposure,
            "daily_gp": w["gross_profit"].sum() / exposure,
            "margin_pct": 100 * w["gross_profit"].sum() / w["revenue"].sum() if w["revenue"].sum() else 0.0,
            "exposure": exposure,
            "units": w["units"].sum(),
            "revenue": w["revenue"].sum(),
            "gp": w["gross_profit"].sum(),
            "discount_cost": w["discount_cost"].sum(),
        }

    rows = []
    for _, pr in promos.iterrows():
        cat = pr["scope_value"]
        base = window_stats(cat, pr["start_date"] - pd.Timedelta(days=BASELINE_DAYS),
                            pr["start_date"] - pd.Timedelta(days=1), clean_only=True)
        promo = window_stats(cat, pr["start_date"], pr["end_date"])
        post = window_stats(cat, pr["end_date"] + pd.Timedelta(days=1),
                            pr["end_date"] + pd.Timedelta(days=DIP_DAYS))
        assert base and promo and post, f"missing window for {pr['promo_id']}"
        incr_units = (promo["daily_units"] - base["daily_units"]) * promo["exposure"]
        incr_rev = (promo["daily_revenue"] - base["daily_revenue"]) * promo["exposure"]
        incr_gp = promo["gp"] - base["daily_gp"] * promo["exposure"]
        rows.append({
            "promo_id": pr["promo_id"], "campaign_name": pr["campaign_name"],
            "category": cat, "promo_type": pr["promo_type"],
            "discount_pct": int(pr["discount_pct"]),
            "start_date": pr["start_date"].date().isoformat(), "end_date": pr["end_date"].date().isoformat(),
            "baseline_daily_units": round(base["daily_units"], 3),
            "promo_daily_units": round(promo["daily_units"], 3),
            "uplift_pct": round(100 * (promo["daily_units"] - base["daily_units"]) / base["daily_units"], 2),
            "incremental_units": round(incr_units),
            "incremental_revenue": round(incr_rev, 2),
            "incremental_gross_profit": round(incr_gp, 2),
            "discount_cost": round(promo["discount_cost"], 2),
            "promo_roi": round(incr_gp / promo["discount_cost"], 3) if promo["discount_cost"] else 0.0,
            "margin_pct_baseline": round(base["margin_pct"], 2),
            "margin_pct_promo": round(promo["margin_pct"], 2),
            "post_promo_dip_pct": round(100 * (base["daily_units"] - post["daily_units"]) / base["daily_units"], 2),
            "promo_units": int(promo["units"]), "promo_revenue": round(promo["revenue"], 2),
        })
    camp = pd.DataFrame(rows).sort_values("promo_roi", ascending=False)
    camp.to_csv("outputs/campaign_performance.csv", index=False)

    bucket = (camp.groupby("discount_pct")
              .apply(lambda g: pd.Series({
                  "campaigns": len(g),
                  "avg_uplift_pct": round(np.average(g["uplift_pct"], weights=g["promo_units"]), 2),
                  "incremental_units": int(g["incremental_units"].sum()),
                  "incremental_revenue": round(g["incremental_revenue"].sum(), 2),
                  "incremental_gross_profit": round(g["incremental_gross_profit"].sum(), 2),
                  "discount_cost": round(g["discount_cost"].sum(), 2),
                  "promo_roi": round(g["incremental_gross_profit"].sum() / g["discount_cost"].sum(), 3),
                  "margin_pct_baseline": round(np.average(g["margin_pct_baseline"], weights=g["promo_units"]), 2),
                  "margin_pct_promo": round(np.average(g["margin_pct_promo"], weights=g["promo_units"]), 2),
                  "avg_post_promo_dip_pct": round(g["post_promo_dip_pct"].mean(), 2),
              })).reset_index())
    bucket.to_csv("outputs/uplift_by_discount_bucket.csv", index=False)

    total_dc = camp["discount_cost"].sum()
    total_igp = camp["incremental_gross_profit"].sum()
    best_bucket = bucket.loc[bucket["promo_roi"].idxmax()]
    worst_bucket = bucket.loc[bucket["promo_roi"].idxmin()]
    worst_camp = camp.loc[camp["promo_roi"].idxmin()]
    best_camp = camp.loc[camp["promo_roi"].idxmax()]
    kpis = [
        ("total_revenue_usd", round(sales["revenue"].sum(), 2)),
        ("total_units", int(sales["units"].sum())),
        ("num_campaigns", len(camp)),
        ("total_discount_cost_usd", round(total_dc, 2)),
        ("total_incremental_revenue_usd", round(camp["incremental_revenue"].sum(), 2)),
        ("total_incremental_gross_profit_usd", round(total_igp, 2)),
        ("overall_promo_roi", round(total_igp / total_dc, 3)),
        ("avg_uplift_pct_weighted", round(np.average(camp["uplift_pct"], weights=camp["promo_units"]), 2)),
        ("avg_margin_pct_baseline", round(np.average(camp["margin_pct_baseline"], weights=camp["promo_units"]), 2)),
        ("avg_margin_pct_promo", round(np.average(camp["margin_pct_promo"], weights=camp["promo_units"]), 2)),
        ("avg_post_promo_dip_pct", round(camp["post_promo_dip_pct"].mean(), 2)),
        ("best_discount_bucket_pct", int(best_bucket["discount_pct"])),
        ("best_bucket_roi", float(best_bucket["promo_roi"])),
        ("worst_discount_bucket_pct", int(worst_bucket["discount_pct"])),
        ("worst_bucket_roi", float(worst_bucket["promo_roi"])),
        ("best_campaign", best_camp["campaign_name"]),
        ("best_campaign_roi", float(best_camp["promo_roi"])),
        ("worst_campaign", worst_camp["campaign_name"]),
        ("worst_campaign_roi", float(worst_camp["promo_roi"])),
        ("worst_campaign_uplift_pct", float(worst_camp["uplift_pct"])),
        ("worst_campaign_margin_pct_promo", float(worst_camp["margin_pct_promo"])),
    ]
    kdf = pd.DataFrame(kpis, columns=["kpi", "value"])
    kdf.to_csv("outputs/kpi_summary.csv", index=False)
    kv = dict(zip(kdf["kpi"], kdf["value"]))

    with open("outputs/insights.md", "w") as f:
        f.write("# Insights — Promotion Effectiveness & Price Analytics (Portfolio Project, synthetic data)\n\n")
        f.write("> Portfolio project — not paid work experience. Synthetic data only.\n\n")
        f.write("## Headline KPIs\n")
        for k, v in kpis:
            f.write(f"- **{k}**: {v}\n")
        f.write("\n## Findings\n")
        f.write(f"- Best discount bucket: **{kv['best_discount_bucket_pct']}% off** with promo ROI of "
                f"{kv['best_bucket_roi']} — incremental gross profit earned per $1 of discount given away.\n")
        f.write(f"- Worst discount bucket: **{kv['worst_discount_bucket_pct']}% off** (ROI {kv['worst_bucket_roi']}). "
                "Deeper is not better: margin % falls faster than units rise.\n")
        f.write(f"- Worst campaign: **{kv['worst_campaign']}** — ROI {kv['worst_campaign_roi']}, uplift only "
                f"{kv['worst_campaign_uplift_pct']}% while promo margin fell to {kv['worst_campaign_margin_pct_promo']}%. "
                "Deep discounting a low-elasticity category destroys margin without buying volume.\n")
        f.write(f"- Pull-forward is real: sales dip an average of **{kv['avg_post_promo_dip_pct']}%** below baseline in the "
                "week after a campaign ends, so part of promo 'uplift' is borrowed from next week's demand.\n")
        f.write(f"- Margin compression: average gross margin falls from {kv['avg_margin_pct_baseline']}% at baseline to "
                f"{kv['avg_margin_pct_promo']}% during promotions.\n")
        f.write(f"- Best campaign: **{kv['best_campaign']}** (ROI {kv['best_campaign_roi']}).\n")
        f.write("\n## Method & assumptions\n")
        f.write("- Baseline = 28 clean days (no promo, no dip week) immediately before each campaign, same category.\n")
        f.write("- Uplift is measured per SKU-store-day so campaigns of different lengths/scopes are comparable.\n")
        f.write("- Cannibalisation across categories is NOT modelled; the post-promo dip captures within-category pull-forward only.\n")
        f.write("- Promo ROI = incremental gross profit / discount cost. ROI > 0 means the discount paid for itself.\n")

    print(kdf.to_string(index=False))
    print("\nWrote outputs/campaign_performance.csv, outputs/uplift_by_discount_bucket.csv, outputs/insights.md")

if __name__ == "__main__":
    main()
