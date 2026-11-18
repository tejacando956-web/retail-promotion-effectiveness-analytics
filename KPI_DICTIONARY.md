# KPI Dictionary — Promotion Effectiveness & Price Analytics

The 15 headline KPIs in `outputs/kpi_summary.csv`, explained in plain words:
what each one means, exactly how it is calculated, what it is worth in the
current run, and which output file it comes from. All money is in US dollars.
The data is synthetic (made up by a script, with a fixed seed so it never
changes).

## Words used in this dictionary

- **SKU** — one product (for example, one TV model). This project has 40 SKUs.
- **Category** — a product group: Laptops, TVs, Appliances, Audio or Accessories.
- **Campaign** — one promotion: a discount (10%, 20%, 30% or 40% off) on one
  category, in all 5 stores, for a set number of days. There are 12 campaigns.
- **Gross profit** — the money left from a sale after paying for the product
  itself: revenue − (units sold × unit cost). It is *before* shop rent, wages
  and other running costs.
- **Margin % (gross margin %)** — gross profit as a share of revenue:
  100 × gross profit ÷ revenue. A 45% margin means the shop keeps 45 cents of
  gross profit from every $1 sold.
- **Baseline** — "normal" trading, used as the comparison point. For each
  campaign the baseline is the **28 days immediately before the campaign**,
  for the same category. One exception: the first two campaigns start too
  early in the data for a full 28 days to exist before them (P01 starts
  13 January, P02 starts 27 January), so all the clean days available were
  used — 12 days for P01 and 19 days for P02.
- **Clean day** — a day with no promotion running in that category and not in
  the 7 days just after a promotion ended. Only clean days are used for
  baselines, so one campaign cannot pollute another campaign's baseline.
- **Exposure / SKU-store-day** — one product, in one store, on one day. Rates
  are measured per SKU-store-day so a 7-day campaign and a 10-day campaign can
  be compared fairly. A window's exposure is the count of its SKU-store-days.
- **Daily rate** — a window total divided by its exposure, e.g. daily units =
  units sold in the window ÷ SKU-store-days in the window.
- **Uplift** — how much more was sold per day during a promotion than in the
  baseline, as a percentage.
- **Incremental** — "extra, caused by the promotion": the promotion window's
  actual result minus what the same window would have done at baseline rates.
- **Discount cost** — the money given away by cutting prices: what the units
  sold on promotion would have cost at full price minus what was actually
  charged. Per sales row: units × full price × discount % ÷ 100.
- **Promo ROI** — return on investment of a promotion: incremental gross
  profit ÷ discount cost. ROI of +0.10 means every $1 of discount earned back
  $0.10 of extra gross profit. ROI below 0 means the promotion lost money.
- **Post-promo dip (pull-forward)** — after a promotion ends, sales fall below
  normal for about a week, because some shoppers bought early to get the deal
  instead of buying later at full price. The dip measures that fall.
- **Percentage points (pts)** — the plain difference between two percentages.
  A margin falling from 45% to 24% fell by 21 percentage points.
- **Weighted average** — an average where bigger items count more. Campaign
  averages here are weighted by units sold on promotion, so a big campaign
  counts more than a small one.
- **Bucket** — a discount-depth group: all campaigns at 10% off form the
  "10% bucket", and so on.

## How every campaign number is built (the campaign-window method)

For each campaign, three windows of daily sales rows (`data/sales.csv`,
joined to `data/products.csv` for prices and costs) are compared:

1. **Baseline window** — the 28 clean days before the campaign, same category. (For P01 and P02, which start in January before 28 days of data exist, all the clean days available are used — 12 days and 19 days.)
2. **Promo window** — the campaign's start date to end date, same category.
3. **Post window** — the 7 days right after the campaign ends, same category.

Per sales row: revenue is as recorded in the data (units × full price ×
(1 − discount % ÷ 100)); gross profit = revenue − units × unit cost;
discount cost = units × full price × discount % ÷ 100 (0 on normal days).

Per campaign (in `outputs/campaign_performance.csv`):

- **uplift %** = 100 × (promo daily units − baseline daily units) ÷ baseline daily units
- **incremental units** = (promo daily units − baseline daily units) × promo exposure
- **incremental revenue** = (promo daily revenue − baseline daily revenue) × promo exposure
- **incremental gross profit** = promo window gross profit − (baseline daily gross profit × promo exposure)
- **discount cost** = sum of the per-row discount cost over the promo window
- **promo ROI** = incremental gross profit ÷ discount cost
- **margin % (baseline / promo)** = 100 × window gross profit ÷ window revenue
- **post-promo dip %** = 100 × (baseline daily units − post-window daily units) ÷ baseline daily units

## The 15 headline KPIs

### Money totals and overall performance

| KPI | Value in this run | What it means (plain words) | Exact calculation | Source |
|---|---|---|---|---|
| total_revenue_usd | 38581528.48 | All money taken at the tills in the 180 days. | Sum of `revenue` over all 36,000 rows of `data/sales.csv`. | data/sales.csv |
| avg_uplift_pct_weighted | 60.38 | On average, promotions sold 60.38% more units per day than normal — weighted so big campaigns count more. | Weighted average of the 12 campaigns' `uplift_pct`, weighted by `promo_units` (units sold during each campaign): Σ(uplift % × promo units) ÷ Σ promo units. | outputs/campaign_performance.csv |
| total_incremental_revenue_usd | 1500802.28 | Extra revenue the promotions caused, over and above what those same days would have taken at normal rates. | Sum of `incremental_revenue` over the 12 campaigns (formula above). | outputs/campaign_performance.csv |
| total_incremental_gross_profit_usd | -427082.45 | Extra gross profit the promotions caused. Negative: overall, promotions destroyed $427,082 of gross profit. | Sum of `incremental_gross_profit` over the 12 campaigns (formula above). | outputs/campaign_performance.csv |
| total_discount_cost_usd | 2126618.7 | Total money given away in price cuts across all 12 campaigns. | Sum of `discount_cost` over the 12 campaigns in `outputs/campaign_performance.csv`; each campaign's discount cost is the sum of units × full price × discount % ÷ 100 over its promo-window rows. | outputs/campaign_performance.csv |
| overall_promo_roi | -0.201 | For every $1 given away in discounts, the promotions lost about $0.20 of gross profit. | total_incremental_gross_profit_usd ÷ total_discount_cost_usd = −427082.45 ÷ 2126618.70, rounded to 3 decimals. | outputs/kpi_summary.csv (from campaign_performance.csv) |
| avg_margin_pct_baseline | 45.01 | Average gross margin on normal (baseline) days, weighted by promo units. | Weighted average of the 12 campaigns' `margin_pct_baseline`, weighted by `promo_units`. | outputs/campaign_performance.csv |
| avg_margin_pct_promo | 24.11 | Average gross margin during promotions, weighted the same way. The gap vs 45.01% is the margin the discounts cost. | Weighted average of the 12 campaigns' `margin_pct_promo`, weighted by `promo_units`. | outputs/campaign_performance.csv |
| avg_post_promo_dip_pct | 18.28 | In the week after a campaign ends, daily unit sales fall on average 18.28% below normal — part of the promo "win" was borrowed from the following week. | Simple (unweighted) mean of the 12 campaigns' `post_promo_dip_pct`. | outputs/campaign_performance.csv |
| profitable_campaigns | 4 | How many of the 12 campaigns made money (ROI above 0). The other 8 lost money. | Count of campaigns with `promo_roi` > 0. | outputs/campaign_performance.csv |

### Best and worst campaigns

| KPI | Value in this run | What it means (plain words) | Exact calculation | Source |
|---|---|---|---|---|
| best_campaign_roi | 0.179 | The best campaign's ROI — Home Refresh Appliances 10%: $0.179 of extra gross profit per $1 of discount. | The highest `promo_roi` in `outputs/campaign_performance.csv` = its incremental gross profit ÷ discount cost = 8,701.68 ÷ 48,537.49, rounded to 3 decimals. | outputs/campaign_performance.csv |
| worst_campaign_roi (label: Accessories Mega Clearance 40%) | -0.951 | The worst campaign's ROI: Accessories Mega Clearance 40% lost $0.951 of gross profit per $1 of discount given away. Its 40% price cut bought only 7.1% more units per day, and it sold at a −9.83% margin — below cost (both figures are in its row of `outputs/campaign_performance.csv`). | Its `promo_roi` = −51,009.81 ÷ 53,621.30, rounded to 3 decimals. | outputs/campaign_performance.csv |

### Discount buckets (discount-depth groups)

Buckets are in `outputs/uplift_by_discount_bucket.csv`. Inside a bucket:
money figures are summed over its campaigns; uplift and margin % are
weighted averages (weight = promo units); bucket ROI = summed incremental
gross profit ÷ summed discount cost; dip % is a simple mean.

| KPI | Value in this run | What it means (plain words) | Exact calculation | Source |
|---|---|---|---|---|
| best_bucket_roi | 0.084 | ROI of the 10% bucket — the best discount depth: each $1 of discount earned back $0.084 of extra gross profit. It is the only depth that made money. | That bucket's summed incremental gross profit ÷ summed discount cost (18,428.62 ÷ 218,956.26), rounded to 3 decimals. | outputs/uplift_by_discount_bucket.csv |
| worst_bucket_roi | -0.387 | ROI of the 40% bucket — the worst discount depth: each $1 of discount lost about $0.39 of gross profit. | That bucket's summed incremental gross profit ÷ summed discount cost (−340,110.75 ÷ 878,602.14), rounded to 3 decimals. | outputs/uplift_by_discount_bucket.csv |

### Where the discount money went

| KPI | Value in this run | What it means (plain words) | Exact calculation | Source |
|---|---|---|---|---|
| laptops_discount_cost_share_pct | 58.21 | Laptops took 58.21% of all the discount money given away ($1,237,977.97 of $2,126,618.70) — because laptop prices are high, each percent off costs more dollars. Laptop discount policy alone decides whether the chain's promotions make or lose money. | 100 × Laptops' summed `discount_cost` ÷ total discount cost, from `outputs/campaign_performance.csv`, rounded to 2 decimals. | outputs/campaign_performance.csv |

## Supporting detail — where the rest lives

These 15 are the headline set, not the whole analysis. The full supporting
detail stays in the breakdown files, and every figure quoted in the README,
dashboard and insights traces back to one of them:

- **`outputs/campaign_performance.csv`** — all 12 campaigns with uplift,
  incremental units/revenue/gross profit, discount cost, ROI, both margins
  and dip % per campaign (including the worst campaign's 7.1% uplift and
  −9.83% promo margin). The campaign count itself — 12 — is scope, read
  from this file's row count, not a headline KPI.
- **`outputs/uplift_by_discount_bucket.csv`** — the four discount buckets
  (10/20/30/40% off) with campaigns, weighted uplift, money sums, ROI and
  margins per bucket.
- **`outputs/profit_bridge.csv`** — the waterfall steps: baseline gross
  profit $2,452,109.49 + uplift gross profit $1,699,536.25 − discount cost
  $2,126,618.70 = promo gross profit $2,025,027.04 (the gross profit actually
  earned inside the promo windows — a bridge step, not a headline KPI).
- **`outputs/promo_by_store.csv`** — the same campaign-window method run
  inside each store: incremental profit, discount cost and ROI per store.
  Best store ST05 at −0.187, worst store ST01 at −0.223; all five stores
  lost money.
- **`outputs/margin_by_category_discount.csv`** — gross margin % for every
  category × discount level from the raw daily rows (the heatmap source;
  extremes: Audio at no discount 55.44%, Accessories at 40% off −9.83%).
- **`data/sales.csv`** — daily revenue detail behind the box plot (median
  daily revenue $215,371.15 on the 105 promotion days vs $205,348.04 on the
  75 normal days) and the category revenue shares behind the donut
  (Laptops 41.92% of revenue).
