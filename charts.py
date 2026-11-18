"""Generate the 10 dashboard charts (matplotlib, dpi=150) from data/outputs.
Run: python3 charts.py  (after generate_data.py and analysis.py)"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

# Retail palette — "warm retail, controlled": rich, warm, no neon/candy,
# no yellow/gold, no navy. Grey is used only for totals/context, never for
# a key data series.
CAT_COLORS = {"Laptops": "#6C4AB0", "TVs": "#C4503F", "Appliances": "#D97D36",
              "Audio": "#C2517E", "Accessories": "#5E8C4A"}
LEVEL_COLORS = {10: "#D98E6A", 20: "#C4503F", 30: "#9C4A6E", 40: "#6C4AB0"}
ROI_POS, ROI_NEG = "#5E8C4A", "#C0392B"
TOTAL_GREY = "#5D6D7E"
SLATE = "#37474f"  # annotation text and context lines only

plt.rcParams.update({"figure.dpi": 150, "axes.titlesize": 12, "axes.grid": True,
                     "grid.alpha": 0.3, "font.size": 10,
                     "figure.facecolor": "white", "axes.facecolor": "white"})

def save(fig, name):
    fig.tight_layout(); fig.savefig(f"images/{name}"); plt.close(fig)
    print("wrote", f"images/{name}")

bucket = pd.read_csv("outputs/uplift_by_discount_bucket.csv")
camp = pd.read_csv("outputs/campaign_performance.csv")
bridge = pd.read_csv("outputs/profit_bridge.csv")
mg = pd.read_csv("outputs/margin_by_category_discount.csv")
sales = pd.read_csv("data/sales.csv", parse_dates=["date"])
products = pd.read_csv("data/products.csv")

# 1) Promo ROI by discount bucket (bars), with each bucket's uplift annotated
fig, ax = plt.subplots(figsize=(7, 4.2))
bars = ax.bar(bucket["discount_pct"].astype(int).astype(str) + "% off",
              bucket["promo_roi"],
              color=[LEVEL_COLORS[int(d)] for d in bucket["discount_pct"]])
ax.axhline(0, color=SLATE, linewidth=1.0)
ax.bar_label(bars, labels=[f"{v:+.2f}" for v in bucket["promo_roi"]],
             padding=3, fontweight="bold")
for bar, up in zip(bars, bucket["avg_uplift_pct"]):
    y = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2, y + (0.075 if y >= 0 else -0.055),
            f"uplift {up:+.1f}%", ha="center",
            va="bottom" if y >= 0 else "top", fontsize=9, color=SLATE)
ax.set_ylim(-0.52, 0.27)
ax.set_ylabel("Promo ROI (extra gross profit per $1 of discount)")
ax.set_xlabel("Discount bucket")
ax.set_title("Promo ROI by Discount Bucket — only 10% off pays for itself")
save(fig, "roi_by_discount_bucket.png")

# 2) Scatter: discount depth vs ROI, one dot per campaign (bubble = discount cost)
camp_s = camp.reset_index(drop=True)
fig, ax = plt.subplots(figsize=(8, 5))
jit = ((np.arange(len(camp_s)) % 3) - 1) * 0.7
sizes = 90 + 900 * camp_s["discount_cost"] / camp_s["discount_cost"].max()
for cat, g in camp_s.groupby("category"):
    ax.scatter(g["discount_pct"] + jit[g.index], g["promo_roi"],
               s=sizes[g.index], color=CAT_COLORS[cat], alpha=0.85,
               edgecolor="white", linewidth=0.9, label=cat)
ax.axhline(0, color=SLATE, linewidth=1.0)
best = camp_s.loc[camp_s["promo_roi"].idxmax()]
worst = camp_s.loc[camp_s["promo_roi"].idxmin()]
for row, off, ha in ((best, (12, 8), "left"), (worst, (-12, -30), "right")):
    ax.annotate(f"{row['campaign_name']}\nROI {row['promo_roi']:.2f}",
                xy=(row["discount_pct"], row["promo_roi"]),
                xytext=off, textcoords="offset points",
                fontsize=9, color=SLATE, ha=ha,
                arrowprops=dict(arrowstyle="-", color=SLATE, linewidth=0.8))
ax.set_xticks([10, 20, 30, 40]); ax.set_xticklabels(["10% off", "20% off", "30% off", "40% off"])
ax.set_xlim(5, 46); ax.set_ylim(-1.22, 0.48)
ax.set_xlabel("Discount depth"); ax.set_ylabel("Promo ROI")
ax.legend(title="Category", loc="lower left")
ax.set_title("Deeper Discounts, Worse ROI — the biggest giveaways lost the most")
save(fig, "discount_roi_scatter.png")

# 3) Profit waterfall: baseline GP -> + uplift GP -> - discount cost -> promo GP
b = dict(zip(bridge["step"], bridge["amount_usd"]))
vals = [b["baseline_gross_profit"], b["uplift_gross_profit"],
        b["discount_cost"], b["promo_gross_profit"]]
labels = ["Baseline gross profit\n(expected)", "+ Extra units sold\n(at full price)",
          "− Discounts\ngiven away", "Promo gross profit\n(actual)"]
colors = [TOTAL_GREY, ROI_POS, ROI_NEG, TOTAL_GREY]
fig, ax = plt.subplots(figsize=(8, 4.6))
peak = vals[0] + vals[1]
ax.set_ylim(0, peak * 1.14)
off = peak * 0.018
cum = 0.0
for i, (v, lab, col) in enumerate(zip(vals, labels, colors)):
    if i in (0, 3):  # total bars start at zero
        if i == 3:
            ax.plot([i - 0.6, i - 0.4], [cum, cum], color=SLATE, linewidth=0.8, linestyle="--")
        ax.bar(i, v, color=col)
        ax.text(i, v + off, f"${v:,.0f}", ha="center", fontsize=10, fontweight="bold")
        cum = v
    else:            # floating delta bars
        ax.plot([i - 0.6, i - 0.4], [cum, cum], color=SLATE, linewidth=0.8, linestyle="--")
        ax.bar(i, v, bottom=cum, color=col)
        top = cum + v
        ax.text(i, max(top, cum) + off, f"{'+' if v >= 0 else '−'}${abs(v):,.0f}",
                ha="center", fontsize=10, fontweight="bold")
        cum = top
ax.set_xticks(range(4)); ax.set_xticklabels(labels, fontsize=9)
ax.set_ylabel("Gross profit ($)")
ax.yaxis.set_major_formatter(lambda v, p: f"${v/1e6:.1f}M")
ax.set_title("Profit Waterfall — promotions earned on volume, then gave back more in discounts")
save(fig, "profit_waterfall.png")

# 4) Heatmap: gross margin % by category x discount level (daily sales rows).
# Single-family warm ramp: deep brick = margin gone (negative cells shout),
# near-white = healthy margin.
piv = mg.pivot(index="category", columns="discount_pct", values="margin_pct")
piv = piv.reindex(index=["Laptops", "TVs", "Appliances", "Audio", "Accessories"],
                  columns=[0, 10, 20, 30, 40])
cmap = LinearSegmentedColormap.from_list(
    "warm_margin", ["#8F2318", "#C0392B", "#D98E6A", "#F6E3D3", "#FFFFFF"])
cmap.set_bad("#E9E6E1")
fig, ax = plt.subplots(figsize=(8.6, 4.6))
arr = piv.values.astype(float)
im = ax.imshow(np.ma.masked_invalid(arr), cmap=cmap, vmin=-15, vmax=60, aspect="auto")
ax.set_xticks(range(5)); ax.set_xticklabels(["No discount", "10% off", "20% off", "30% off", "40% off"])
ax.set_yticks(range(5)); ax.set_yticklabels(piv.index)
for i in range(arr.shape[0]):
    for j in range(arr.shape[1]):
        if np.isnan(arr[i, j]):
            txt, col = "no promo\nrun", SLATE
        else:
            txt = f"{arr[i, j]:.1f}%"
            col = "white" if (arr[i, j] + 15) / 75 < 0.45 else SLATE
        ax.text(j, i, txt, ha="center", va="center", fontsize=9.5,
                color=col, fontweight="bold")
ax.grid(False)
ax.set_xlabel("Discount level"); ax.set_ylabel("Category")
ax.set_title("Margin Melts as the Discount Deepens — Accessories at 40% off sold below cost")
cbar = fig.colorbar(im, ax=ax, shrink=0.9, pad=0.02)
cbar.set_label("Gross margin %")
save(fig, "margin_heatmap.png")

# 5) Box plot: daily revenue on promotion days vs normal days
promo_dates = set(sales.loc[sales["promo_id"].notna(), "date"])
daily_rev = sales.groupby("date")["revenue"].sum()
promo_vals = daily_rev[daily_rev.index.isin(promo_dates)].values
normal_vals = daily_rev[~daily_rev.index.isin(promo_dates)].values
fig, ax = plt.subplots(figsize=(7, 4.4))
bp = ax.boxplot([promo_vals, normal_vals], patch_artist=True,
                medianprops=dict(color="white", linewidth=2.0),
                boxprops=dict(edgecolor=SLATE), whiskerprops=dict(color=SLATE),
                capprops=dict(color=SLATE), flierprops=dict(markerfacecolor=SLATE, markeredgecolor=SLATE))
ax.set_xticklabels([f"Promotion days\n(n={len(promo_vals)})", f"Normal days\n(n={len(normal_vals)})"])
for patch, col in zip(bp["boxes"], ["#C4503F", "#5E8C4A"]):
    patch.set_facecolor(col); patch.set_alpha(0.88)
for i, series in enumerate([promo_vals, normal_vals], start=1):
    med = np.median(series)
    ax.text(i, med + 9000, f"median ${med:,.0f}", ha="center", fontsize=10, fontweight="bold")
ax.set_ylabel("Revenue per day ($)")
ax.yaxis.set_major_formatter(lambda v, p: f"${v/1000:,.0f}K")
ax.set_title("Promotion Days Take a Little More Money — at Much Thinner Margin")
save(fig, "daily_revenue_boxplot.png")

# 6) Donut: revenue share by category
sales_cat = sales.merge(products[["sku_id", "category"]], on="sku_id", how="left")
cat_rev = sales_cat.groupby("category")["revenue"].sum().sort_values(ascending=False)
total_rev = cat_rev.sum()
fig, ax = plt.subplots(figsize=(8.4, 4.8))
wedges, _ = ax.pie(cat_rev.values, colors=[CAT_COLORS[c] for c in cat_rev.index],
                   startangle=90, counterclock=False,
                   wedgeprops=dict(width=0.42, edgecolor="white", linewidth=1.5))
ax.legend(wedges, [f"{c} — ${v/1e6:.2f}M ({100*v/total_rev:.1f}%)" for c, v in cat_rev.items()],
          loc="center left", bbox_to_anchor=(0.90, 0.5), fontsize=10)
ax.text(0, 0, f"Total\n${total_rev/1e6:.1f}M", ha="center", va="center",
        fontsize=12, fontweight="bold", color=SLATE)
ax.set_title("Revenue Share by Category — Laptops alone bring in 41.9% of all revenue")
save(fig, "category_revenue_donut.png")

# 7) Promotion results by store: incremental gross profit bars + ROI markers
store = pd.read_csv("outputs/promo_by_store.csv")  # already sorted best ROI first
fig, ax = plt.subplots(figsize=(8, 4.6))
bars = ax.bar(store["store_id"], store["incremental_gross_profit"],
              color=[ROI_POS if v >= 0 else ROI_NEG for v in store["incremental_gross_profit"]])
ax.set_ylim(min(store["incremental_gross_profit"]) * 1.18, 6000)
for bar, v in zip(bars, store["incremental_gross_profit"]):
    ax.text(bar.get_x() + bar.get_width() / 2, v * 0.90,
            f"${v:,.0f}", ha="center", va="center",
            fontsize=10, fontweight="bold", color="white")
ax.axhline(0, color=SLATE, linewidth=0.9)
ax.set_ylabel("Incremental gross profit ($)")
ax.yaxis.set_major_formatter(lambda v, p: f"${v/1000:,.0f}K")
ax2 = ax.twinx()
ax2.plot(store["store_id"], store["promo_roi"], color=CAT_COLORS["Laptops"], marker="D",
         markersize=7, linewidth=1.6, markeredgecolor="white")
ax2.set_ylim(store["promo_roi"].min() - 0.012, store["promo_roi"].max() + 0.016)
for i, r in enumerate(store["promo_roi"]):
    ax2.annotate(f"ROI {r:.2f}", (i, r), textcoords="offset points",
                 xytext=(0, 11), ha="center", fontsize=9.5, color=CAT_COLORS["Laptops"],
                 fontweight="bold")
ax2.set_ylabel("Promo ROI (per $1 of discount)")
ax2.grid(False)
ax.set_title("Promotions Lost Money in Every Store — each judged against its own baseline")
ax.set_xlabel("Stores ordered best to worst promo ROI")
save(fig, "promo_results_by_store.png")

# 8) Scatter: uplift % vs margin change (percentage points), one dot per campaign
camp_m = camp.copy()
camp_m["margin_change_pp"] = camp_m["margin_pct_promo"] - camp_m["margin_pct_baseline"]
fig, ax = plt.subplots(figsize=(8, 5))
sizes_m = 90 + 900 * camp_m["discount_cost"] / camp_m["discount_cost"].max()
for cat, g in camp_m.groupby("category"):
    ax.scatter(g["uplift_pct"], g["margin_change_pp"], s=sizes_m[g.index],
               color=CAT_COLORS[cat], alpha=0.85, edgecolor="white",
               linewidth=0.9, label=cat)
ax.axhline(0, color=SLATE, linewidth=1.0)
ax.axvline(0, color=SLATE, linewidth=1.0)
ax.set_xlim(-8, 158); ax.set_ylim(-52, 5)
least_loss = camp_m.loc[camp_m["margin_change_pp"].idxmax()]
biggest_loss = camp_m.loc[camp_m["margin_change_pp"].idxmin()]
for row, off, ha, tag in ((least_loss, (12, 12), "left", "smallest margin loss"),
                          (biggest_loss, (18, 16), "left", "biggest margin loss")):
    ax.annotate(f"{row['campaign_name']}\n{tag}: {row['margin_change_pp']:.1f} pts",
                xy=(row["uplift_pct"], row["margin_change_pp"]),
                xytext=off, textcoords="offset points",
                fontsize=9, color=SLATE, ha=ha,
                arrowprops=dict(arrowstyle="-", color=SLATE, linewidth=0.8))
ax.set_xlabel("Unit uplift vs baseline (%)")
ax.set_ylabel("Margin change (promo margin % − baseline margin %, points)")
ax.legend(title="Category", loc="upper right")
ax.set_title("Uplift vs Margin Change — more sales always cost margin; the question is how much")
save(fig, "uplift_margin_scatter.png")

# 9) Post-promo dip by campaign (horizontal bar, biggest dip at top)
d = camp.sort_values("post_promo_dip_pct")
fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.barh(d["campaign_name"], d["post_promo_dip_pct"],
               color=[CAT_COLORS[c] for c in d["category"]])
ax.bar_label(bars, fmt="%.1f%%", padding=2)
ax.set_xlim(0, 24.5)
ax.set_xlabel("Fall in daily units in the 7 days after the campaign, vs baseline (%)")
ax.set_title("Post-Promo Dip by Campaign — the hangover after every offer")
save(fig, "dip_by_campaign.png")

# 10) Total discount cost by category (vertical bar, $ and share labelled)
dc_cat = (camp.groupby("category")["discount_cost"].sum()
          .reindex(["Laptops", "TVs", "Audio", "Appliances", "Accessories"])
          .sort_values(ascending=False))
dc_total = dc_cat.sum()
fig, ax = plt.subplots(figsize=(7.5, 4.4))
bars = ax.bar(dc_cat.index, dc_cat.values,
              color=[CAT_COLORS[c] for c in dc_cat.index])
ax.bar_label(bars, labels=[f"${v:,.0f} · {100*v/dc_total:.1f}%" for v in dc_cat.values],
             padding=2)
ax.set_ylabel("Discount cost given away ($)")
ax.yaxis.set_major_formatter(lambda v, p: f"${v/1e6:.1f}M")
ax.set_ylim(0, dc_cat.max() * 1.16)
ax.set_title("Discount Cost by Category — laptops took over half of all discount money")
save(fig, "discount_cost_by_category.png")
