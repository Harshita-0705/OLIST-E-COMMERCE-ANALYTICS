"""
OLIST E-COMMERCE ANALYTICS ENGINE
Real data only: olist_orders_dataset.csv, olist_order_items_dataset.csv, olist_order_reviews_dataset.csv
"""

import pandas as pd
import numpy as np

# ─── LOAD & BUILD MASTER DATASET ──────────────────────────────────────────────
def load_data():
    orders  = pd.read_csv('olist_orders_dataset.csv')
    items   = pd.read_csv('olist_order_items_dataset.csv')
    reviews = pd.read_csv('olist_order_reviews_dataset.csv')

    date_cols = ['order_purchase_timestamp','order_approved_at',
                 'order_delivered_carrier_date','order_delivered_customer_date',
                 'order_estimated_delivery_date']
    for c in date_cols:
        orders[c] = pd.to_datetime(orders[c], errors='coerce')

    # Revenue per order
    order_revenue = (items.groupby('order_id')
                     .agg(revenue=('price','sum'), freight=('freight_value','sum'))
                     .reset_index())

    # Best review per order (some orders have multiple reviews)
    best_review = (reviews.sort_values('review_score', ascending=False)
                   .drop_duplicates('order_id')[['order_id','review_score']])

    master = (orders
              .merge(order_revenue, on='order_id', how='left')
              .merge(best_review,   on='order_id', how='left'))

    delivered = master['order_status'] == 'delivered'
    master['delivery_days'] = np.where(
        delivered,
        (master['order_delivered_customer_date'] - master['order_purchase_timestamp']).dt.days,
        np.nan
    )
    master['delay_days'] = np.where(
        delivered,
        (master['order_delivered_customer_date'] - master['order_estimated_delivery_date']).dt.days,
        np.nan
    )
    master['is_late'] = master['delay_days'] > 0
    master['purchase_month'] = master['order_purchase_timestamp'].dt.to_period('M')

    return master, items, reviews


def kpi_summary(master):
    total   = len(master)
    deliv   = (master['order_status'] == 'delivered').sum()
    cancel  = (master['order_status'] == 'canceled').sum()
    revenue = master.loc[master['order_status']=='delivered','revenue'].sum()
    aov     = master.loc[master['order_status']=='delivered','revenue'].mean()
    avg_del = master['delivery_days'].mean()
    late_pct= master.loc[master['order_status']=='delivered','is_late'].mean() * 100
    avg_rev = master['review_score'].mean()
    return {
        'total_orders':    int(total),
        'delivered_orders':int(deliv),
        'canceled_orders': int(cancel),
        'delivery_rate':   round(deliv / total * 100, 2),
        'cancel_rate':     round(cancel / total * 100, 2),
        'total_revenue':   round(revenue, 2),
        'avg_order_value': round(aov, 2),
        'avg_delivery_days': round(avg_del, 1),
        'late_delivery_pct': round(late_pct, 2),
        'avg_review_score':  round(avg_rev, 2),
    }


# ─── FUNNEL ───────────────────────────────────────────────────────────────────
FUNNEL_ORDER = ['created','approved','invoiced','processing','shipped','delivered']

def build_funnel(master):
    counts = master['order_status'].value_counts()
    # Only keep funnel stages that exist in data
    stages = [s for s in FUNNEL_ORDER if s in counts.index]
    users  = [counts[s] for s in stages]

    df = pd.DataFrame({'stage': stages, 'orders': users})
    first_val = df['orders'].iloc[0] if len(df) > 0 else 1
    df['pct_of_total']   = (df['orders'] / first_val * 100).round(2)
    df['conversion_rate']= df['pct_of_total']
    df['dropoff_pct']    = (1 - df['orders'] / df['orders'].shift(1)).fillna(0).mul(100).round(2)

    # Cancellation separate
    cancel_count = counts.get('canceled', 0)
    total        = len(master) if len(master) > 0 else 1
    cancel_pct   = round(cancel_count / total * 100, 2)
    return df, cancel_count, cancel_pct


# ─── MONTHLY REVENUE ──────────────────────────────────────────────────────────
def monthly_revenue(master):
    df = (master[master['order_status']=='delivered']
          .groupby('purchase_month')
          .agg(revenue=('revenue','sum'), orders=('order_id','count'))
          .reset_index())
    df['purchase_month'] = df['purchase_month'].astype(str)
    df['mom_growth'] = df['revenue'].pct_change().mul(100).round(2)
    return df


# ─── COHORT ANALYSIS ──────────────────────────────────────────────────────────
def cohort_analysis(master):
    """Returns a monthly summary DataFrame with columns:
    cohort, orders, avg_revenue, avg_review, late_pct
    (Olist customer_id is unique per order — true retention cohorts not possible)
    """
    df = master[master['order_status'] == 'delivered'].copy()
    df['cohort'] = df['order_purchase_timestamp'].dt.to_period('M').astype(str)

    result = (df.groupby('cohort')
              .agg(
                  orders=('order_id', 'count'),
                  avg_revenue=('revenue', 'mean'),
                  avg_review=('review_score', 'mean'),
                  late_pct=('is_late', 'mean'),
              )
              .reset_index())
    result['avg_revenue'] = result['avg_revenue'].round(2)
    result['avg_review']  = result['avg_review'].round(2)
    result['late_pct']    = (result['late_pct'] * 100).round(2)
    return result


# ─── CUSTOMER ANALYTICS ───────────────────────────────────────────────────────
def customer_analytics(master):
    df = master[master['order_status']=='delivered'].copy()
    cust = (df.groupby('customer_id')
            .agg(
                total_orders=('order_id','count'),
                total_revenue=('revenue','sum'),
                first_order=('order_purchase_timestamp','min'),
                last_order=('order_purchase_timestamp','max'),
            ).reset_index())
    cust['clv']          = cust['total_revenue']
    cust['is_repeat']    = cust['total_orders'] > 1
    cust['order_freq']   = cust['total_orders']

    # Revenue segments
    cust['revenue_segment'] = pd.cut(
        cust['clv'],
        bins=[0, 100, 300, 1000, float('inf')],
        labels=['Low (<R$100)', 'Mid (R$100-300)', 'High (R$300-1k)', 'Premium (R$1k+)']
    )

    # Review segments — merge review_score from master
    avg_review = df.groupby('customer_id')['review_score'].mean().reset_index()
    cust = cust.merge(avg_review, on='customer_id', how='left')
    cust['review_segment'] = pd.cut(
        cust['review_score'],
        bins=[0, 2, 3, 5],
        labels=['Detractor', 'Passive', 'Promoter']
    )

    total_customers = len(cust)
    repeat_customers= cust['is_repeat'].sum()
    new_customers   = total_customers - repeat_customers
    repeat_rate     = round(repeat_customers / total_customers * 100, 2)
    avg_clv         = round(cust['clv'].mean(), 2)
    avg_freq        = round(cust['order_freq'].mean(), 2)

    summary = {
        'total_customers':   total_customers,
        'repeat_customers':  int(repeat_customers),
        'new_customers':     int(new_customers),
        'repeat_rate':       repeat_rate,
        'avg_clv':           avg_clv,
        'avg_order_freq':    avg_freq,
    }
    return cust, summary


# ─── DELIVERY ANALYSIS ────────────────────────────────────────────────────────
def delivery_analysis(master):
    df = master[master['order_status']=='delivered'].dropna(subset=['delivery_days']).copy()

    def bucket(d):
        if d <= 7:   return '0-7d'
        elif d <= 14: return '8-14d'
        elif d <= 30: return '15-30d'
        else:         return '30d+'

    df['delivery_bucket'] = df['delivery_days'].apply(bucket)
    bucket_order = ['0-7d','8-14d','15-30d','30d+']

    by_bucket = (df.groupby('delivery_bucket')
                 .agg(orders=('order_id','count'),
                      avg_review=('review_score','mean'),
                      late_pct=('is_late','mean'))
                 .reindex(bucket_order)
                 .reset_index())
    by_bucket['avg_review'] = by_bucket['avg_review'].round(2)
    by_bucket['late_pct']   = (by_bucket['late_pct'] * 100).round(2)

    return df, by_bucket


# ─── NPS & REVIEW ANALYSIS ────────────────────────────────────────────────────
def nps_analysis(reviews):
    total = len(reviews)
    promoters  = (reviews['review_score'] == 5).sum()
    passives   = reviews['review_score'].isin([3,4]).sum()
    detractors = reviews['review_score'].isin([1,2]).sum()

    nps = round((promoters - detractors) / total * 100, 2)

    dist = (reviews['review_score'].value_counts()
            .sort_index().reset_index())
    dist.columns = ['score','count']
    dist['pct'] = (dist['count'] / total * 100).round(2)

    reviews = reviews.copy()
    reviews['review_creation_date'] = pd.to_datetime(reviews['review_creation_date'], errors='coerce')
    reviews['month'] = reviews['review_creation_date'].dt.to_period('M').astype(str)
    monthly = (reviews.groupby('month')['review_score']
               .agg(['mean','count']).reset_index())
    monthly.columns = ['month','avg_score','review_count']

    return {
        'nps': nps,
        'promoters_pct':  round(promoters/total*100, 2),
        'passives_pct':   round(passives/total*100, 2),
        'detractors_pct': round(detractors/total*100, 2),
        'promoters':  int(promoters),
        'passives':   int(passives),
        'detractors': int(detractors),
    }, dist, monthly


# ─── PRODUCT & SELLER ANALYSIS ────────────────────────────────────────────────
def product_seller_analysis(items, master):
    delivered_ids = set(master.loc[master['order_status']=='delivered','order_id'])
    df = items[items['order_id'].isin(delivered_ids)].copy()

    top_products = (df.groupby('product_id')
                    .agg(revenue=('price','sum'),
                         orders=('order_id','nunique'),
                         avg_price=('price','mean'),
                         avg_freight=('freight_value','mean'))
                    .reset_index()
                    .sort_values('revenue', ascending=False)
                    .head(15))

    top_sellers = (df.groupby('seller_id')
                   .agg(revenue=('price','sum'),
                        orders=('order_id','nunique'),
                        products=('product_id','nunique'))
                   .reset_index()
                   .sort_values('revenue', ascending=False)
                   .head(15))

    price_freight = df[['price','freight_value']].dropna()
    return top_products, top_sellers, price_freight


# ─── BUSINESS INSIGHTS ────────────────────────────────────────────────────────
def generate_insights(kpis, cust_summary, nps_data, delivery_df, by_bucket):
    insights = []

    # Cancellation
    if kpis['cancel_rate'] > 2:
        insights.append(('warning', f"Cancellation rate is {kpis['cancel_rate']}% — investigate payment/stock issues"))

    # Late delivery impact
    late_avg = delivery_df[delivery_df['is_late']]['review_score'].mean()
    ontime_avg = delivery_df[~delivery_df['is_late']]['review_score'].mean()
    if not pd.isna(late_avg):
        diff = round(ontime_avg - late_avg, 2)
        insights.append(('error', f"Late deliveries score {late_avg:.2f} vs {ontime_avg:.2f} on-time — {diff} point gap"))

    # One-time buyers
    if cust_summary['repeat_rate'] < 10:
        insights.append(('warning', f"Only {cust_summary['repeat_rate']}% customers repeat — strong one-time buyer problem"))

    # NPS
    nps = nps_data['nps']
    if nps > 0:
        insights.append(('success', f"NPS score is {nps} — positive, but room to grow (industry avg ~45)"))
    else:
        insights.append(('error', f"NPS score is {nps} — negative, detractors outweigh promoters"))

    # Delivery time
    if kpis['avg_delivery_days'] > 14:
        insights.append(('warning', f"Avg delivery is {kpis['avg_delivery_days']} days — customers expect under 7"))

    # Revenue concentration
    insights.append(('info', f"Avg CLV: R${cust_summary['avg_clv']:,.2f} | Avg orders/customer: {cust_summary['avg_order_freq']}"))

    return insights
