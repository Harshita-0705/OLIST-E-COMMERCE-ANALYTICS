-- ============================================================
-- OLIST E-COMMERCE ANALYTICS (REAL DATA ONLY)
-- No simulated tables (no events/users)
-- Tables: olist_orders_dataset
--         olist_order_items_dataset
--         olist_order_reviews_dataset
-- Compatible with: PostgreSQL / DuckDB
-- ============================================================


-- ─────────────────────────────────────────
-- 1. KPI SUMMARY
-- ─────────────────────────────────────────
SELECT
    COUNT(*)                                                                 AS total_orders,
    SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END)             AS delivered_orders,
    SUM(CASE WHEN order_status = 'canceled'  THEN 1 ELSE 0 END)             AS canceled_orders,
    ROUND(
        SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END)
        * 100.0 / COUNT(*), 2
    )                                                                        AS delivery_rate_pct
FROM olist_orders_dataset;


-- ─────────────────────────────────────────
-- 2. ORDER FUNNEL (REAL)
-- ─────────────────────────────────────────
SELECT
    order_status,
    COUNT(*)                                                    AS orders,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2)          AS percentage
FROM olist_orders_dataset
GROUP BY order_status
ORDER BY orders DESC;


-- ─────────────────────────────────────────
-- 3. MONTHLY REVENUE
-- ─────────────────────────────────────────
SELECT
    DATE_TRUNC('month', o.order_purchase_timestamp)  AS month,
    SUM(i.price)                                     AS revenue,
    COUNT(DISTINCT o.order_id)                       AS orders
FROM olist_orders_dataset      o
JOIN olist_order_items_dataset i ON o.order_id = i.order_id
WHERE o.order_status = 'delivered'
GROUP BY 1
ORDER BY 1;


-- ─────────────────────────────────────────
-- 4. AVG ORDER VALUE
-- ─────────────────────────────────────────
SELECT
    ROUND(AVG(order_total), 2) AS avg_order_value
FROM (
    SELECT order_id, SUM(price) AS order_total
    FROM olist_order_items_dataset
    GROUP BY order_id
) t;


-- ─────────────────────────────────────────
-- 5. DELIVERY PERFORMANCE
-- ─────────────────────────────────────────
SELECT
    ROUND(AVG(
        DATE_PART('day', order_delivered_customer_date - order_purchase_timestamp)
    ), 2)                                                                    AS avg_delivery_days,
    ROUND(
        SUM(CASE WHEN order_delivered_customer_date > order_estimated_delivery_date
                 THEN 1 ELSE 0 END)
        * 100.0 / COUNT(*), 2
    )                                                                        AS late_delivery_pct
FROM olist_orders_dataset
WHERE order_status = 'delivered';


-- ─────────────────────────────────────────
-- 6. DELIVERY TIME VS REVIEW SCORE
-- ─────────────────────────────────────────
SELECT
    CASE
        WHEN DATE_PART('day', o.order_delivered_customer_date - o.order_purchase_timestamp) <= 7
            THEN '0-7d'
        WHEN DATE_PART('day', o.order_delivered_customer_date - o.order_purchase_timestamp) <= 14
            THEN '8-14d'
        WHEN DATE_PART('day', o.order_delivered_customer_date - o.order_purchase_timestamp) <= 30
            THEN '15-30d'
        ELSE '30d+'
    END                                  AS delivery_bucket,
    COUNT(*)                             AS orders,
    ROUND(AVG(r.review_score), 2)        AS avg_review_score
FROM olist_orders_dataset         o
JOIN olist_order_reviews_dataset  r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY delivery_bucket
ORDER BY delivery_bucket;


-- ─────────────────────────────────────────
-- 7. REVIEW SCORE DISTRIBUTION
-- ─────────────────────────────────────────
SELECT
    review_score,
    COUNT(*)                                                   AS count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2)         AS percentage
FROM olist_order_reviews_dataset
GROUP BY review_score
ORDER BY review_score;


-- ─────────────────────────────────────────
-- 8. NPS SCORE
-- ─────────────────────────────────────────
WITH scores AS (
    SELECT
        COUNT(*) FILTER (WHERE review_score = 5)  * 100.0 / COUNT(*) AS promoters_pct,
        COUNT(*) FILTER (WHERE review_score <= 2) * 100.0 / COUNT(*) AS detractors_pct
    FROM olist_order_reviews_dataset
)
SELECT
    ROUND(promoters_pct,   2) AS promoters_pct,
    ROUND(detractors_pct,  2) AS detractors_pct,
    ROUND(promoters_pct - detractors_pct, 2) AS nps_score
FROM scores;


-- ─────────────────────────────────────────
-- 9. TOP 10 PRODUCTS BY REVENUE
-- ─────────────────────────────────────────
SELECT
    product_id,
    SUM(price)              AS revenue,
    COUNT(DISTINCT order_id) AS orders,
    ROUND(AVG(price), 2)    AS avg_price
FROM olist_order_items_dataset
GROUP BY product_id
ORDER BY revenue DESC
LIMIT 10;


-- ─────────────────────────────────────────
-- 10. TOP 10 SELLERS BY REVENUE
-- ─────────────────────────────────────────
SELECT
    seller_id,
    SUM(price)               AS revenue,
    COUNT(DISTINCT order_id) AS orders,
    COUNT(DISTINCT product_id) AS products_sold
FROM olist_order_items_dataset
GROUP BY seller_id
ORDER BY revenue DESC
LIMIT 10;


-- ─────────────────────────────────────────
-- 11. CUSTOMER REPEAT RATE
-- Note: Olist customer_id is unique per order.
--       Repeat rate here = 0 by design of the dataset.
--       Use this query to confirm and document that fact.
-- ─────────────────────────────────────────
WITH customer_orders AS (
    SELECT
        customer_id,
        COUNT(order_id) AS total_orders
    FROM olist_orders_dataset
    GROUP BY customer_id
)
SELECT
    COUNT(*)                                                          AS total_customers,
    COUNT(*) FILTER (WHERE total_orders > 1)                         AS repeat_customers,
    ROUND(
        COUNT(*) FILTER (WHERE total_orders > 1) * 100.0 / COUNT(*), 2
    )                                                                 AS repeat_customer_rate_pct
FROM customer_orders;


-- ─────────────────────────────────────────
-- 12. MONTHLY ORDER COHORT ANALYSIS
--     (order volume + avg revenue + avg review per month)
-- ─────────────────────────────────────────
SELECT
    DATE_TRUNC('month', o.order_purchase_timestamp)  AS cohort_month,
    COUNT(DISTINCT o.order_id)                       AS total_orders,
    ROUND(SUM(i.price) / COUNT(DISTINCT o.order_id), 2) AS avg_order_value,
    ROUND(AVG(r.review_score), 2)                    AS avg_review_score,
    ROUND(
        SUM(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
                 THEN 1 ELSE 0 END)
        * 100.0 / COUNT(DISTINCT o.order_id), 2
    )                                                AS late_delivery_pct
FROM olist_orders_dataset         o
JOIN olist_order_items_dataset    i ON o.order_id = i.order_id
LEFT JOIN olist_order_reviews_dataset r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
GROUP BY 1
ORDER BY 1;


-- ─────────────────────────────────────────
-- 13. REVENUE CONCENTRATION (TOP SELLER SHARE)
-- ─────────────────────────────────────────
WITH seller_revenue AS (
    SELECT
        seller_id,
        SUM(price) AS revenue
    FROM olist_order_items_dataset
    GROUP BY seller_id
),
total AS (
    SELECT SUM(price) AS total_revenue FROM olist_order_items_dataset
)
SELECT
    s.seller_id,
    ROUND(s.revenue, 2)                                    AS revenue,
    ROUND(s.revenue * 100.0 / t.total_revenue, 2)          AS revenue_share_pct
FROM seller_revenue s
CROSS JOIN total t
ORDER BY revenue DESC
LIMIT 15;


-- ─────────────────────────────────────────
-- 14. PRICE VS FREIGHT ANALYSIS
-- ─────────────────────────────────────────
SELECT
    ROUND(AVG(price), 2)                                    AS avg_item_price,
    ROUND(AVG(freight_value), 2)                            AS avg_freight,
    ROUND(AVG(freight_value / NULLIF(price, 0)) * 100, 2)  AS avg_freight_pct_of_price,
    ROUND(MIN(price), 2)                                    AS min_price,
    ROUND(MAX(price), 2)                                    AS max_price
FROM olist_order_items_dataset;


-- ─────────────────────────────────────────
-- 15. MONTHLY REVIEW TREND
-- ─────────────────────────────────────────
SELECT
    DATE_TRUNC('month', review_creation_date)  AS month,
    COUNT(*)                                   AS total_reviews,
    ROUND(AVG(review_score), 2)                AS avg_score,
    COUNT(*) FILTER (WHERE review_score = 5)   AS promoters,
    COUNT(*) FILTER (WHERE review_score <= 2)  AS detractors
FROM olist_order_reviews_dataset
WHERE review_creation_date IS NOT NULL
GROUP BY 1
ORDER BY 1;
