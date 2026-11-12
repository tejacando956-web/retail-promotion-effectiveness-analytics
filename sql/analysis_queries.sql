-- Promotion Effectiveness & Price Analytics - SQL pack (standard SQL / BigQuery-SQL style)
-- Tables: sales(date, sku_id, store_id, units, revenue, discount_pct_applied, promo_id),
--         products(sku_id, product_name, category, base_price, unit_cost),
--         promotions(promo_id, campaign_name, scope_type, scope_value, start_date, end_date, discount_pct, promo_type)
-- Convention: gross_profit = revenue - units * unit_cost. 'Clean' baseline days =
-- no promotion and not in the 7-day post-promo dip window of any campaign in that category.

-- Q1. Daily sales trend with promotion flag ------------------------------------------------
SELECT s.date,
       SUM(s.units) AS units,
       SUM(s.revenue) AS revenue,
       MAX(CASE WHEN s.promo_id IS NOT NULL THEN 1 ELSE 0 END) AS any_promo_day
FROM sales s
GROUP BY s.date
ORDER BY s.date;

-- Q2. Gross margin % by discount bucket ----------------------------------------------------
SELECT s.discount_pct_applied AS discount_bucket,
       SUM(s.units) AS units,
       SUM(s.revenue) AS revenue,
       SUM(s.revenue - s.units * p.unit_cost) AS gross_profit,
       100.0 * SUM(s.revenue - s.units * p.unit_cost) / SUM(s.revenue) AS margin_pct
FROM sales s JOIN products p USING (sku_id)
GROUP BY discount_bucket
ORDER BY discount_bucket;

-- Q3. Campaign scorecard: units, revenue, gross profit, discount cost ----------------------
SELECT pr.promo_id, pr.campaign_name, pr.discount_pct,
       SUM(s.units) AS promo_units,
       SUM(s.revenue) AS promo_revenue,
       SUM(s.revenue - s.units * p.unit_cost) AS gross_profit,
       SUM(s.units * p.base_price * s.discount_pct_applied / 100.0) AS discount_cost,
       100.0 * SUM(s.revenue - s.units * p.unit_cost) / SUM(s.revenue) AS margin_pct
FROM sales s
JOIN products p USING (sku_id)
JOIN promotions pr ON pr.promo_id = s.promo_id
GROUP BY pr.promo_id, pr.campaign_name, pr.discount_pct
ORDER BY gross_profit DESC;

-- Q4. Matched baseline: average daily units per SKU-store in the 28 clean days pre-campaign
WITH dip AS (  -- (category, dip_date) pairs: 7 days after each campaign ends
  SELECT pr.scope_value AS category,
         DATE_ADD(pr.end_date, INTERVAL n DAY) AS dip_date
  FROM promotions pr
  JOIN UNNEST(GENERATE_ARRAY(1, 7)) AS n
)
SELECT pr.promo_id,
       SUM(s.units) / COUNT(DISTINCT CONCAT(CAST(s.date AS STRING), s.sku_id, s.store_id)) AS baseline_daily_units
FROM promotions pr
JOIN sales s
  ON s.date BETWEEN DATE_SUB(pr.start_date, INTERVAL 28 DAY) AND DATE_SUB(pr.start_date, INTERVAL 1 DAY)
JOIN products p ON p.sku_id = s.sku_id AND p.category = pr.scope_value
WHERE s.promo_id IS NULL
  AND NOT EXISTS (SELECT 1 FROM dip d WHERE d.category = pr.scope_value AND d.dip_date = s.date)
GROUP BY pr.promo_id;

-- Q5. Uplift: promotion-window daily rate vs baseline daily rate (uses Q4 logic as CTEs) ----
WITH base AS (
  SELECT pr.promo_id,
         SUM(s.units) * 1.0 / COUNT(DISTINCT CONCAT(CAST(s.date AS STRING), s.sku_id, s.store_id)) AS daily_units
  FROM promotions pr
  JOIN sales s ON s.date BETWEEN DATE_SUB(pr.start_date, INTERVAL 28 DAY) AND DATE_SUB(pr.start_date, INTERVAL 1 DAY)
              AND s.promo_id IS NULL
  JOIN products p ON p.sku_id = s.sku_id AND p.category = pr.scope_value
  GROUP BY pr.promo_id
),
promo AS (
  SELECT promo_id,
         SUM(units) * 1.0 / COUNT(DISTINCT CONCAT(CAST(date AS STRING), sku_id, store_id)) AS daily_units
  FROM sales WHERE promo_id IS NOT NULL GROUP BY promo_id
)
SELECT pr.campaign_name, pr.discount_pct,
       b.daily_units AS baseline_daily_units,
       p.daily_units AS promo_daily_units,
       100.0 * (p.daily_units - b.daily_units) / b.daily_units AS uplift_pct
FROM promotions pr
JOIN base b USING (promo_id) JOIN promo p USING (promo_id)
ORDER BY uplift_pct DESC;

-- Q6. Post-promo dip: daily units in the 7 days after each campaign vs its baseline --------
SELECT pr.campaign_name,
       AVG(day_units.units) AS post_promo_daily_units
FROM promotions pr
JOIN (
  SELECT p.category, s.date, SUM(s.units) / COUNT(DISTINCT CONCAT(s.sku_id, s.store_id)) AS units
  FROM sales s JOIN products p USING (sku_id)
  GROUP BY p.category, s.date
) day_units
  ON day_units.category = pr.scope_value
 AND day_units.date BETWEEN DATE_ADD(pr.end_date, INTERVAL 1 DAY) AND DATE_ADD(pr.end_date, INTERVAL 7 DAY)
GROUP BY pr.campaign_name;
-- Compare with Q4 baseline: dip_pct = 100 * (baseline - post) / baseline. Positive = pull-forward dip.

-- Q7. Campaign ranking with RANK(): best and worst promo ROI -------------------------------
WITH camp AS (
  SELECT pr.campaign_name,
         SUM(s.revenue - s.units * p.unit_cost) AS gross_profit,
         SUM(s.units * p.base_price * s.discount_pct_applied / 100.0) AS discount_cost
  FROM sales s JOIN products p USING (sku_id) JOIN promotions pr ON pr.promo_id = s.promo_id
  GROUP BY pr.campaign_name
)
SELECT campaign_name, gross_profit, discount_cost,
       RANK() OVER (ORDER BY gross_profit DESC) AS rank_by_gross_profit
FROM camp
ORDER BY rank_by_gross_profit;
-- Full ROI in the Python analysis also subtracts expected baseline gross profit; see analysis.py.

-- Q8. 7-day rolling average of daily units (LAG / window frame) ----------------------------
SELECT date, units,
       AVG(units) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS units_7d_avg,
       LAG(units, 7) OVER (ORDER BY date) AS units_same_day_last_week
FROM (SELECT date, SUM(units) AS units FROM sales GROUP BY date)
ORDER BY date;

-- Q9. Category margin during promotions vs clean days --------------------------------------
SELECT p.category,
       CASE WHEN s.promo_id IS NOT NULL THEN 'Promo' ELSE 'Non-promo' END AS period_type,
       SUM(s.units) AS units, SUM(s.revenue) AS revenue,
       100.0 * SUM(s.revenue - s.units * p.unit_cost) / SUM(s.revenue) AS margin_pct
FROM sales s JOIN products p USING (sku_id)
GROUP BY p.category, period_type
ORDER BY p.category, period_type;

-- Q10. The 'bad promo' detector: high discount, low uplift proxy, negative margin -----------
SELECT pr.campaign_name, pr.discount_pct,
       SUM(s.units) AS promo_units,
       100.0 * SUM(s.revenue - s.units * p.unit_cost) / SUM(s.revenue) AS margin_pct
FROM sales s JOIN products p USING (sku_id) JOIN promotions pr ON pr.promo_id = s.promo_id
GROUP BY pr.campaign_name, pr.discount_pct
HAVING margin_pct < 0 OR (pr.discount_pct >= 30 AND margin_pct < 10)
ORDER BY margin_pct;
-- Flags campaigns that sell below cost or trade margin for almost nothing - review before repeating.
