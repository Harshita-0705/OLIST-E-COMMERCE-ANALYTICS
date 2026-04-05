"""
OLIST CHART EXPORTS — Real data only
Generates PNG charts for reports.
Run: python charts.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os, sys

sys.path.insert(0, '.')
from analysis import (load_data, kpi_summary, build_funnel, monthly_revenue,
                      cohort_analysis, customer_analytics, delivery_analysis,
                      nps_analysis, product_seller_analysis)

os.makedirs('charts_output', exist_ok=True)
master, items, reviews = load_data()

COLORS = ['#4A90D9','#5BA85A','#E8A838','#7F77DD','#E05252','#2EC4B6','#8E9AAF']

# ─── 1. FUNNEL ────────────────────────────────────────────────────────────────
funnel_df, cancel_count, cancel_pct = build_funnel(master)
fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.barh(funnel_df['stage'], funnel_df['orders'],
               color=COLORS[:len(funnel_df)], height=0.55)
for bar, row in zip(bars, funnel_df.itertuples()):
    ax.text(bar.get_width() + 200, bar.get_y() + bar.get_height()/2,
            f"{row.orders:,}  ({row.conversion_rate:.1f}%)", va='center', fontsize=10)
ax.set_title('Order Funnel — Real Olist Data', fontsize=14, pad=12)
ax.set_xlabel('Orders')
ax.invert_yaxis()
plt.tight_layout()
plt.savefig('charts_output/01_funnel.png', dpi=150)
plt.close()
print("✅ 01_funnel.png")

# ─── 2. MONTHLY REVENUE ───────────────────────────────────────────────────────
monthly_rev = monthly_revenue(master)
fig, ax = plt.subplots(figsize=(12, 5))
ax.bar(monthly_rev['purchase_month'], monthly_rev['revenue'],
       color='#4A90D9', width=0.7)
ax.set_title('Monthly Revenue (Delivered Orders)', fontsize=14, pad=12)
ax.set_xlabel('Month')
ax.set_ylabel('Revenue (R$)')
ax.tick_params(axis='x', rotation=45)
plt.tight_layout()
plt.savefig('charts_output/02_monthly_revenue.png', dpi=150)
plt.close()
print("✅ 02_monthly_revenue.png")

# ─── 3. COHORT MONTHLY SUMMARY ────────────────────────────────────────────────
cohort_df = cohort_analysis(master)
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].bar(cohort_df['cohort'], cohort_df['orders'], color='#4A90D9')
axes[0].set_title('Monthly Order Volume by Cohort', fontsize=12)
axes[0].set_xlabel('Month')
axes[0].set_ylabel('Orders')
axes[0].tick_params(axis='x', rotation=45)

axes[1].plot(cohort_df['cohort'], cohort_df['avg_review'], marker='o', color='#5BA85A')
axes[1].axhline(4.0, linestyle='--', color='gray', label='Target: 4.0')
axes[1].set_title('Avg Review Score by Month', fontsize=12)
axes[1].set_xlabel('Month')
axes[1].set_ylabel('Avg Review Score')
axes[1].set_ylim(1, 5.5)
axes[1].tick_params(axis='x', rotation=45)
axes[1].legend()
plt.tight_layout()
plt.savefig('charts_output/03_cohort_heatmap.png', dpi=150)
plt.close()
print("✅ 03_cohort_heatmap.png")

# ─── 4. DELIVERY VS REVIEW ────────────────────────────────────────────────────
delivery_df, by_bucket = delivery_analysis(master)
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].bar(by_bucket['delivery_bucket'], by_bucket['avg_review'],
            color=['#5BA85A','#E8A838','#E05252','#7F77DD'])
axes[0].set_title('Avg Review Score by Delivery Speed', fontsize=12)
axes[0].set_ylabel('Avg Review Score')
axes[0].set_ylim(0, 5.5)
for i, row in by_bucket.iterrows():
    axes[0].text(i, row['avg_review'] + 0.05, f"{row['avg_review']:.2f}", ha='center')

axes[1].hist(delivery_df['delivery_days'].dropna(), bins=60, color='#4A90D9', edgecolor='white')
axes[1].axvline(delivery_df['delivery_days'].mean(), color='red', linestyle='--',
                label=f"Avg: {delivery_df['delivery_days'].mean():.1f}d")
axes[1].set_title('Delivery Time Distribution', fontsize=12)
axes[1].set_xlabel('Days')
axes[1].set_ylabel('Orders')
axes[1].legend()
plt.tight_layout()
plt.savefig('charts_output/04_delivery_analysis.png', dpi=150)
plt.close()
print("✅ 04_delivery_analysis.png")

# ─── 5. NPS ───────────────────────────────────────────────────────────────────
nps_data, rev_dist, monthly_reviews = nps_analysis(reviews)
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].bar(rev_dist['score'], rev_dist['count'],
            color=['#E05252','#E05252','#E8A838','#E8A838','#5BA85A'])
for i, row in rev_dist.iterrows():
    axes[0].text(row['score'], row['count'] + 200, f"{row['pct']:.1f}%", ha='center')
axes[0].set_title('Review Score Distribution', fontsize=12)
axes[0].set_xlabel('Review Score')
axes[0].set_ylabel('Count')

labels = ['Promoters\n(5★)', 'Passives\n(3-4★)', 'Detractors\n(1-2★)']
sizes  = [nps_data['promoters_pct'], nps_data['passives_pct'], nps_data['detractors_pct']]
axes[1].pie(sizes, labels=labels, autopct='%1.1f%%',
            colors=['#5BA85A','#E8A838','#E05252'], startangle=90)
axes[1].set_title(f"NPS Breakdown — Score: {nps_data['nps']}", fontsize=12)
plt.tight_layout()
plt.savefig('charts_output/05_nps.png', dpi=150)
plt.close()
print("✅ 05_nps.png")

# ─── 6. TOP SELLERS ───────────────────────────────────────────────────────────
top_products, top_sellers, _ = product_seller_analysis(items, master)
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
ts = top_sellers.head(10).copy()
ts['seller_id'] = ts['seller_id'].str[:10] + '...'
axes[0].barh(ts['seller_id'], ts['revenue'], color='#5BA85A')
axes[0].set_title('Top 10 Sellers by Revenue', fontsize=12)
axes[0].set_xlabel('Revenue (R$)')
axes[0].invert_yaxis()

tp = top_products.head(10).copy()
tp['product_id'] = tp['product_id'].str[:10] + '...'
axes[1].barh(tp['product_id'], tp['revenue'], color='#4A90D9')
axes[1].set_title('Top 10 Products by Revenue', fontsize=12)
axes[1].set_xlabel('Revenue (R$)')
axes[1].invert_yaxis()
plt.tight_layout()
plt.savefig('charts_output/06_top_sellers_products.png', dpi=150)
plt.close()
print("✅ 06_top_sellers_products.png")

# ─── 7. CUSTOMER SEGMENTS ─────────────────────────────────────────────────────
cust_df, cust_sum = customer_analytics(master)
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].pie([cust_sum['new_customers'], cust_sum['repeat_customers']],
            labels=['New (1 order)', 'Repeat (2+ orders)'],
            autopct='%1.1f%%', colors=['#4A90D9','#5BA85A'], startangle=90)
axes[0].set_title('New vs Repeat Customers', fontsize=12)

freq = cust_df['total_orders'].value_counts().sort_index()
freq = freq[freq.index <= 10]
axes[1].bar(freq.index, freq.values, color='#7F77DD')
axes[1].set_title('Order Frequency Distribution', fontsize=12)
axes[1].set_xlabel('Orders per Customer')
axes[1].set_ylabel('Customers')
plt.tight_layout()
plt.savefig('charts_output/07_customer_segments.png', dpi=150)
plt.close()
print("✅ 07_customer_segments.png")

print("\n✅ All charts saved to charts_output/")
