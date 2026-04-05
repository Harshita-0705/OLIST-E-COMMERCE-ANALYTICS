# 🛒 Olist E-Commerce Analytics Dashboard

Interactive analytics dashboard built with Streamlit using real Brazilian e-commerce data from [Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

🔗 **[Live Demo](https://harshita-0705-olist-e-commerce-analytics.streamlit.app)**

---

## Pages

- **Overview** — KPIs, monthly revenue & orders, MoM growth, order status distribution
- **Order Funnel** — Stage-by-stage conversion, drop-off analysis
- **Cohort Retention** — Monthly order volume, avg revenue, review scores, late delivery trends
- **Customer Analytics** — CLV distribution, revenue segments, review segments, delivery speed impact
- **Delivery Analysis** — Delivery time distribution, on-time vs late, review score by speed
- **Products & Sellers** — Top 15 by revenue, price vs freight analysis

## Tech Stack

- Python, Streamlit, Plotly, Pandas
- Dataset: Olist Brazilian E-Commerce (Kaggle)

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Dataset

Place these files in the project root:
- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_order_reviews_dataset.csv`
