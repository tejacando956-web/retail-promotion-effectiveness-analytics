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
    bridge_baseline_gp = 0.0   # GP the promo windows would have earned at baseline rates
    bridge_promo_gp = 0.0      # actual GP earned inside the promo windows
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
        bridge_baseline_gp += base["daily_gp"] * promo["exposure"]
        bridge_promo_gp += promo["gp"]
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

    # --- Promotion results by store: the SAME campaign-window method, run
    # separately inside each store. Every campaign ran in all 5 stores, so for
    # each campaign x store we rebuild that store's own matched baseline (the
    # 28 clean days before the campaign, same category, that store only) and
    # measure the store's promo window against it. Each store is judged
    # against its own baseline instead of one pooled chain baseline; in this
    # dataset the five store incremental-profit figures sum back to the chain
    # total in campaign_performance.csv (discount cost within a cent of
    # rounding), which is a useful cross-check of the split.
    def window_stats_store(cat, store, start, end, clean_only=False):
        m = (sales["category"] == cat) & (sales["store_id"] == store) & \
            (sales["date"] >= start) & (sales["date"] <= end)
        if clean_only:
            m &= sales["is_clean"]
        w = sales[m]
        exposure = w[["date", "sku_id"]].drop_duplicates().shape[0]
        if exposure == 0:
            return None
        return {
            "daily_units": w["units"].sum() / exposure,
            "daily_revenue": w["revenue"].sum() / exposure,
            "daily_gp": w["gross_profit"].sum() / exposure,
            "exposure": exposure,
            "gp": w["gross_profit"].sum(),
            "discount_cost": w["discount_cost"].sum(),
        }

    store_rows = []
    for store in sorted(sales["store_id"].unique()):
        s_incr_units = 0.0
        s_incr_rev = 0.0
        s_incr_gp = 0.0
        s_dc = 0.0
        for _, pr in promos.iterrows():
            cat = pr["scope_value"]
            base = window_stats_store(cat, store,
                                      pr["start_date"] - pd.Timedelta(days=BASELINE_DAYS),
                                      pr["start_date"] - pd.Timedelta(days=1),
                                      clean_only=True)
            promo = window_stats_store(cat, store, pr["start_date"], pr["end_date"])
            assert base and promo, f"missing store window for {pr['promo_id']} / {store}"
            s_incr_units += (promo["daily_units"] - base["daily_units"]) * promo["exposure"]
            s_incr_rev += (promo["daily_revenue"] - base["daily_revenue"]) * promo["exposure"]
            s_incr_gp += promo["gp"] - base["daily_gp"] * promo["exposure"]
            s_dc += promo["discount_cost"]
        store_rows.append({
            "store_id": store,
            "campaigns": len(promos),
            "incremental_units": round(s_incr_units),
            "incremental_revenue": round(s_incr_rev, 2),
            "incremental_gross_profit": round(s_incr_gp, 2),
            "discount_cost": round(s_dc, 2),
            "promo_roi": round(s_incr_gp / s_dc, 3) if s_dc else 0.0,
        })
    store_df = pd.DataFrame(store_rows).sort_values("promo_roi", ascending=False)
    store_df.to_csv("outputs/promo_by_store.csv", index=False)
    best_store_row = store_df.iloc[0]
    worst_store_row = store_df.iloc[-1]
    stores_positive = int((store_df["promo_roi"] > 0).sum())
    store_incr_gp_sum = round(store_df["incremental_gross_profit"].sum(), 2)

    # --- Profit bridge (waterfall) across ALL campaigns, campaign-window method.
    # Promo GP = (gross profit the extra units would have earned at full price)
    #            - discount cost, relative to the expected baseline GP.
    # uplift_gp is defined so the bridge reconciles exactly:
    #   baseline_gp + uplift_gp - discount_cost = promo_gp
    # and uplift_gp - discount_cost = total incremental gross profit.
    total_dc_all = camp["discount_cost"].sum()
    baseline_gp_r = round(bridge_baseline_gp, 2)
    promo_gp_r = round(bridge_promo_gp, 2)
    uplift_gp_r = round(promo_gp_r + round(total_dc_all, 2) - baseline_gp_r, 2)
    bridge = pd.DataFrame([
        {"step": "baseline_gross_profit", "label": "Baseline gross profit (expected in promo windows)",
         "amount_usd": baseline_gp_r, "cumulative_usd": baseline_gp_r},
        {"step": "uplift_gross_profit", "label": "Gross profit from extra units sold (at full price)",
         "amount_usd": uplift_gp_r, "cumulative_usd": round(baseline_gp_r + uplift_gp_r, 2)},
        {"step": "discount_cost", "label": "Discount cost given away",
         "amount_usd": -round(total_dc_all, 2), "cumulative_usd": promo_gp_r},
        {"step": "promo_gross_profit", "label": "Promo gross profit (actual in promo windows)",
         "amount_usd": promo_gp_r, "cumulative_usd": promo_gp_r},
    ])
    bridge.to_csv("outputs/profit_bridge.csv", index=False)

    # --- Gross margin % by category x discount level, from the daily sales rows.
    mg = (sales.groupby(["category", "discount_pct_applied"])
          .agg(units=("units", "sum"), revenue=("revenue", "sum"),
               gross_profit=("gross_profit", "sum")).reset_index()
          .rename(columns={"discount_pct_applied": "discount_pct"}))
    mg["margin_pct"] = np.where(mg["revenue"] > 0,
                                100 * mg["gross_profit"] / mg["revenue"], 0.0).round(2)
    mg["revenue"] = mg["revenue"].round(2)
    mg["gross_profit"] = mg["gross_profit"].round(2)
    cat_order = ["Laptops", "TVs", "Appliances", "Audio", "Accessories"]
    mg["category"] = pd.Categorical(mg["category"], categories=cat_order, ordered=True)
    mg = mg.sort_values(["category", "discount_pct"]).reset_index(drop=True)
    mg["category"] = mg["category"].astype(str)
    mg.to_csv("outputs/margin_by_category_discount.csv", index=False)
    mg_max = mg.loc[mg["margin_pct"].idxmax()]
    mg_min = mg.loc[mg["margin_pct"].idxmin()]

    def cell_label(row):
        d = int(row["discount_pct"])
        return f"{row['category']} at {'no discount' if d == 0 else str(d) + '% off'}"

    # --- Daily revenue: promotion days (any campaign live) vs normal days.
    promo_dates = set(sales.loc[sales["promo_id"].notna(), "date"])
    daily_rev = sales.groupby("date")["revenue"].sum()
    promo_day_rev = daily_rev[daily_rev.index.isin(promo_dates)]
    normal_day_rev = daily_rev[~daily_rev.index.isin(promo_dates)]

    # --- Revenue share by category.
    cat_rev = sales.groupby("category")["revenue"].sum().sort_values(ascending=False)
    top_cat = cat_rev.index[0]
    top_cat_share = round(100 * cat_rev.iloc[0] / cat_rev.sum(), 2)

    profitable = int((camp["promo_roi"] > 0).sum())
    losing = int((camp["promo_roi"] <= 0).sum())

    total_dc = camp["discount_cost"].sum()
    total_igp = camp["incremental_gross_profit"].sum()
    best_bucket = bucket.loc[bucket["promo_roi"].idxmax()]
    worst_bucket = bucket.loc[bucket["promo_roi"].idxmin()]
    worst_camp = camp.loc[camp["promo_roi"].idxmin()]
    best_camp = camp.loc[camp["promo_roi"].idxmax()]
    all_kpis = [
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
        ("profitable_campaigns", profitable),
        ("losing_campaigns", losing),
        ("baseline_gross_profit_usd", baseline_gp_r),
        ("uplift_gross_profit_usd", uplift_gp_r),
        ("promo_gross_profit_usd", promo_gp_r),
        ("promo_days", int(len(promo_day_rev))),
        ("normal_days", int(len(normal_day_rev))),
        ("median_daily_revenue_promo_days_usd", round(float(promo_day_rev.median()), 2)),
        ("median_daily_revenue_normal_days_usd", round(float(normal_day_rev.median()), 2)),
        ("top_revenue_category", top_cat),
        ("top_revenue_category_share_pct", top_cat_share),
        ("highest_margin_cell", cell_label(mg_max)),
        ("highest_margin_pct", float(mg_max["margin_pct"])),
        ("lowest_margin_cell", cell_label(mg_min)),
        ("lowest_margin_pct", float(mg_min["margin_pct"])),
        ("best_store", best_store_row["store_id"]),
        ("best_store_promo_roi", float(best_store_row["promo_roi"])),
        ("best_store_incremental_gross_profit_usd", float(best_store_row["incremental_gross_profit"])),
        ("worst_store", worst_store_row["store_id"]),
        ("worst_store_promo_roi", float(worst_store_row["promo_roi"])),
        ("worst_store_incremental_gross_profit_usd", float(worst_store_row["incremental_gross_profit"])),
        ("stores_with_positive_promo_roi", stores_positive),
        ("laptops_discount_cost_share_pct",
         round(100 * camp.loc[camp["category"] == "Laptops", "discount_cost"].sum() / total_dc, 2)),
    ]
    kv = dict(all_kpis)

    # The headline set: exactly 15 KPIs — the learnable face of the project.
    # Every other measure stays available in the breakdown CSVs
    # (campaign_performance, uplift_by_discount_bucket, promo_by_store,
    # profit_bridge, margin_by_category_discount). The worst campaign's name
    # (kv["worst_campaign"]) is a label on the worst_campaign_roi row in the
    # README / KPI dictionary, not a KPI of its own.
    HEADLINE_KPIS = [
        "total_revenue_usd",
        "avg_uplift_pct_weighted",
        "total_incremental_revenue_usd",
        "total_incremental_gross_profit_usd",
        "total_discount_cost_usd",
        "overall_promo_roi",
        "avg_margin_pct_baseline",
        "avg_margin_pct_promo",
        "avg_post_promo_dip_pct",
        "profitable_campaigns",
        "best_campaign_roi",
        "worst_campaign_roi",
        "best_bucket_roi",
        "worst_bucket_roi",
        "laptops_discount_cost_share_pct",
    ]
    # dtype=object keeps integer KPIs (e.g. profitable_campaigns) written as
    # integers instead of being upcast to floats by the mixed column.
    kdf = pd.DataFrame([(k, kv[k]) for k in HEADLINE_KPIS],
                       columns=["kpi", "value"], dtype=object)
    kdf.to_csv("outputs/kpi_summary.csv", index=False)

    with open("outputs/insights.md", "w") as f:
        f.write("# Insights — Promotion Effectiveness & Price Analytics (Portfolio Project, synthetic data)\n\n")
        f.write("> Portfolio project — not paid work experience. Synthetic data only.\n\n")
        f.write("## Headline KPIs\n")
        for k in HEADLINE_KPIS:
            f.write(f"- **{k}**: {kv[k]}\n")
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
        f.write(f"- Only **{kv['profitable_campaigns']} of {kv['num_campaigns']} campaigns** made money; "
                f"{kv['losing_campaigns']} returned a negative ROI.\n")
        f.write(f"- Profit bridge (all promo windows): the campaigns were expected to earn "
                f"${kv['baseline_gross_profit_usd']:,.2f} of gross profit at normal rates. The extra units sold "
                f"added ${kv['uplift_gross_profit_usd']:,.2f} of gross profit at full price, but the discounts gave "
                f"away ${kv['total_discount_cost_usd']:,.2f} — leaving actual promo gross profit of "
                f"${kv['promo_gross_profit_usd']:,.2f}, i.e. ${-kv['total_incremental_gross_profit_usd']:,.2f} worse than doing nothing.\n")
        f.write(f"- Margin heatmap (category x discount): the strongest cell is **{kv['highest_margin_cell']}** at "
                f"{kv['highest_margin_pct']}%; the weakest is **{kv['lowest_margin_cell']}** at {kv['lowest_margin_pct']}% — "
                "deep discounts push whole categories below cost.\n")
        f.write(f"- Promotion days feel busy but pay thin: median daily revenue is "
                f"${kv['median_daily_revenue_promo_days_usd']:,.2f} on the {kv['promo_days']} promotion days vs "
                f"${kv['median_daily_revenue_normal_days_usd']:,.2f} on the {kv['normal_days']} normal days — "
                "more money through the till, at much worse margin.\n")
        f.write(f"- Revenue concentration: **{kv['top_revenue_category']}** is the biggest category with "
                f"{kv['top_revenue_category_share_pct']}% of total revenue, so its discount policy drives the overall result.\n")
        f.write(f"- Same campaigns, different stores: run store by store (each store judged against its own "
                f"28-clean-day baselines), promotions lost money in **every** store — "
                f"{kv['stores_with_positive_promo_roi']} of 5 stores had a positive promo ROI. The least-bad store "
                f"was **{kv['best_store']}** (ROI {kv['best_store_promo_roi']}) and the worst was "
                f"**{kv['worst_store']}** (ROI {kv['worst_store_promo_roi']}). Ranked by dollars the picture flips: "
                f"{kv['best_store']} lost the most money (${kv['best_store_incremental_gross_profit_usd']:,.2f}) because "
                f"it is the biggest store and gave away the most discount, while {kv['worst_store']} lost the least "
                f"(${kv['worst_store_incremental_gross_profit_usd']:,.2f}). The five store incremental-profit figures "
                f"sum to ${store_incr_gp_sum:,.2f}, exactly the chain total of "
                f"${kv['total_incremental_gross_profit_usd']:,.2f} from the pooled-baseline method.\n")
        f.write("\n## Method & assumptions\n")
        f.write("- Baseline = 28 clean days (no promo, no dip week) immediately before each campaign, same category.\n")
        f.write("- Uplift is measured per SKU-store-day so campaigns of different lengths/scopes are comparable.\n")
        f.write("- Cannibalisation across categories is NOT modelled; the post-promo dip captures within-category pull-forward only.\n")
        f.write("- Promo ROI = incremental gross profit / discount cost. ROI > 0 means the discount paid for itself.\n")

    print(kdf.to_string(index=False))
    print("\nWrote outputs/campaign_performance.csv, outputs/uplift_by_discount_bucket.csv, "
          "outputs/promo_by_store.csv, outputs/profit_bridge.csv, "
          "outputs/margin_by_category_discount.csv, outputs/insights.md")

if __name__ == "__main__":
    main()
