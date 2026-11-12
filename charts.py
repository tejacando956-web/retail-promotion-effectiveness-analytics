"""Generate the 4 dashboard charts (matplotlib, dpi=150) from data/outputs.
Run: python3 charts.py  (after generate_data.py and analysis.py)"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams.update({"figure.dpi": 150, "axes.titlesize": 12, "axes.grid": True,
                     "grid.alpha": 0.3, "font.size": 10})

def save(fig, name):
    fig.tight_layout(); fig.savefig(f"images/{name}"); plt.close(fig)
    print("wrote", f"images/{name}")

bucket = pd.read_csv("outputs/uplift_by_discount_bucket.csv")
camp = pd.read_csv("outputs/campaign_performance.csv")
sales = pd.read_csv("data/sales.csv", parse_dates=["date"])
promos = pd.read_csv("data/promotions.csv", parse_dates=["start_date", "end_date"])

# 1) Uplift by discount bucket
fig, ax = plt.subplots(figsize=(7, 4))
bars = ax.bar(bucket["discount_pct"].astype(str) + "% off", bucket["avg_uplift_pct"],
              color=["#2e7d32" if v >= 50 else "#f9a825" if v >= 25 else "#c62828" for v in bucket["avg_uplift_pct"]])
ax.bar_label(bars, fmt="%.1f%%", padding=2)
ax.set_ylabel("Avg unit uplift vs baseline (%)"); ax.set_xlabel("Discount bucket")
ax.set_title("Unit Uplift by Discount Bucket — deeper discount, more uplift")
save(fig, "uplift_by_discount_bucket.png")

# 2) Margin: promo vs baseline by bucket
fig, ax = plt.subplots(figsize=(7, 4))
x = range(len(bucket)); w = 0.38
ax.bar([i - w/2 for i in x], bucket["margin_pct_baseline"], w, label="Baseline margin %", color="#455a64")
ax.bar([i + w/2 for i in x], bucket["margin_pct_promo"], w, label="Promo margin %",
       color=["#c62828" if v < 0 else "#f9a825" for v in bucket["margin_pct_promo"]])
ax.axhline(0, color="black", linewidth=0.8)
ax.set_xticks(list(x)); ax.set_xticklabels(bucket["discount_pct"].astype(str) + "% off")
ax.set_ylabel("Gross margin (%)"); ax.legend()
ax.set_title("Gross Margin: Promotion vs Baseline by Discount Bucket")
save(fig, "margin_promo_vs_baseline.png")

# 3) Daily sales timeline with promo periods shaded
daily = sales.groupby("date")["units"].sum()
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(daily.index, daily.values, color="#1565c0", linewidth=1.2)
for _, pr in promos.iterrows():
    ax.axvspan(pr["start_date"], pr["end_date"], color="#f9a825", alpha=0.35)
ax.plot([], [], color="#f9a825", linewidth=8, alpha=0.35, label="Promotion window (any category)")
ax.set_ylabel("Units per day (all stores)"); ax.legend(loc="upper left")
ax.set_title("Daily Unit Sales with Promotion Periods Shaded — spikes, then post-promo dips")
save(fig, "sales_timeline_promo_periods.png")

# 4) ROI by campaign
c = camp.sort_values("promo_roi")
fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.barh(c["campaign_name"], c["promo_roi"],
               color=["#2e7d32" if v >= 0 else "#c62828" for v in c["promo_roi"]])
ax.axvline(0, color="black", linewidth=0.8)
ax.bar_label(bars, fmt="%.2f", padding=2)
ax.set_xlabel("Promo ROI = incremental gross profit / discount cost")
ax.set_title("Promo ROI by Campaign — only shallow discounts pay for themselves")
save(fig, "roi_by_campaign.png")
