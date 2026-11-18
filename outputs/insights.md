# Insights — Promotion Effectiveness & Price Analytics (Portfolio Project, synthetic data)

> Portfolio project — not paid work experience. Synthetic data only.

## Headline KPIs
- **total_revenue_usd**: 38581528.48
- **avg_uplift_pct_weighted**: 60.38
- **total_incremental_revenue_usd**: 1500802.28
- **total_incremental_gross_profit_usd**: -427082.45
- **total_discount_cost_usd**: 2126618.7
- **overall_promo_roi**: -0.201
- **avg_margin_pct_baseline**: 45.01
- **avg_margin_pct_promo**: 24.11
- **avg_post_promo_dip_pct**: 18.28
- **profitable_campaigns**: 4
- **best_campaign_roi**: 0.179
- **worst_campaign_roi**: -0.951
- **best_bucket_roi**: 0.084
- **worst_bucket_roi**: -0.387
- **laptops_discount_cost_share_pct**: 58.21

## Findings
- Best discount bucket: **10% off** with promo ROI of 0.084 — incremental gross profit earned per $1 of discount given away.
- Worst discount bucket: **40% off** (ROI -0.387). Deeper is not better: margin % falls faster than units rise.
- Worst campaign: **Accessories Mega Clearance 40%** — ROI -0.951, uplift only 7.1% while promo margin fell to -9.83%. Deep discounting a low-elasticity category destroys margin without buying volume.
- Pull-forward is real: sales dip an average of **18.28%** below baseline in the week after a campaign ends, so part of promo 'uplift' is borrowed from next week's demand.
- Margin compression: average gross margin falls from 45.01% at baseline to 24.11% during promotions.
- Best campaign: **Home Refresh Appliances 10%** (ROI 0.179).
- Only **4 of 12 campaigns** made money; 8 returned a negative ROI.
- Profit bridge (all promo windows): the campaigns were expected to earn $2,452,109.49 of gross profit at normal rates. The extra units sold added $1,699,536.25 of gross profit at full price, but the discounts gave away $2,126,618.70 — leaving actual promo gross profit of $2,025,027.04, i.e. $427,082.45 worse than doing nothing.
- Margin heatmap (category x discount): the strongest cell is **Audio at no discount** at 55.44%; the weakest is **Accessories at 40% off** at -9.83% — deep discounts push whole categories below cost.
- Promotion days feel busy but pay thin: median daily revenue is $215,371.15 on the 105 promotion days vs $205,348.04 on the 75 normal days — more money through the till, at much worse margin.
- Revenue concentration: **Laptops** is the biggest category with 41.92% of total revenue, so its discount policy drives the overall result.
- Same campaigns, different stores: run store by store (each store judged against its own 28-clean-day baselines), promotions lost money in **every** store — 0 of 5 stores had a positive promo ROI. The least-bad store was **ST05** (ROI -0.187) and the worst was **ST01** (ROI -0.223). Ranked by dollars the picture flips: ST05 lost the most money ($-98,878.16) because it is the biggest store and gave away the most discount, while ST01 lost the least ($-72,204.01). The five store incremental-profit figures sum to $-427,082.45, exactly the chain total of $-427,082.45 from the pooled-baseline method.

## Method & assumptions
- Baseline = 28 clean days (no promo, no dip week) immediately before each campaign, same category.
- Uplift is measured per SKU-store-day so campaigns of different lengths/scopes are comparable.
- Cannibalisation across categories is NOT modelled; the post-promo dip captures within-category pull-forward only.
- Promo ROI = incremental gross profit / discount cost. ROI > 0 means the discount paid for itself.
