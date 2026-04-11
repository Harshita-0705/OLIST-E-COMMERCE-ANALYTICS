"""
OLIST E-COMMERCE PRODUCT ANALYTICS DASHBOARD
Real data only — no simulation.
Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Olist Analytics",
    layout="wide",
    page_icon="🛒",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main .block-container {
        overflow-y: auto;
        max-height: 100vh;
        padding-bottom: 3rem;
    }
    /* Sidebar filter styling */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #8E9AAF;
    }
    section[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {
        background-color: #4A90D9 !important;
        border-radius: 4px;
    }
    .filter-label {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #8E9AAF;
        margin-bottom: 4px;
    }
    .filter-value {
        font-size: 1rem;
        font-weight: 600;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

C = dict(blue="#4A90D9", green="#5BA85A", orange="#E8A838",
         purple="#7F77DD", red="#E05252", teal="#2EC4B6", gray="#8E9AAF")

# ─── LOAD ─────────────────────────────────────────────────────────────────────
@st.cache_data
def load():
    from analysis import load_data
    return load_data()

try:
    master, items, reviews = load()
    data_ok = True
except Exception as e:
    data_ok = False
    load_error = str(e)

if not data_ok:
    st.error(f"Failed to load data: {load_error}")
    st.stop()

# ─── SIDEBAR FILTERS ──────────────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/fluency/96/combo-chart.png", width=55)
st.sidebar.title("Olist Analytics")
st.sidebar.divider()

all_months = sorted(master['purchase_month'].dropna().astype(str).unique())

st.sidebar.markdown("#### 📅 Month Range")
col_s, col_e = st.sidebar.columns(2)
start_month = col_s.selectbox("From", all_months, index=0, label_visibility="collapsed")
end_month   = col_e.selectbox("To",   all_months, index=len(all_months)-1, label_visibility="collapsed")
st.sidebar.caption(f"{start_month}  →  {end_month}")

sel_months = all_months[all_months.index(start_month): all_months.index(end_month) + 1]

st.sidebar.markdown("#### 🏷️ Order Status")
all_statuses = sorted(master['order_status'].unique())
sel_status = []
cols = st.sidebar.columns(2)
for i, s in enumerate(all_statuses):
    if cols[i % 2].checkbox(s, value=True, key=f"status_{s}"):
        sel_status.append(s)

# Apply filters — fallback to all if nothing selected
if not sel_months:
    sel_months = all_months
if not sel_status:
    sel_status = all_statuses

mask = (
    master['purchase_month'].astype(str).isin(sel_months) &
    master['order_status'].isin(sel_status)
)
mf = master[mask].copy()

if len(mf) == 0:
    st.warning("No data for selected filters. Showing all data.")
    mf = master.copy()

st.sidebar.divider()
page = st.sidebar.radio("Navigate", [
    "📈 Overview",
    "🔽 Order Funnel",
    "🔁 Cohort Retention",
    "👥 Customer Analytics",
    "🚚 Delivery Analysis",
    "📦 Products & Sellers",
])

# ─── SHARED COMPUTATIONS ──────────────────────────────────────────────────────
@st.cache_data
def compute(mf_hash, _mf):
    from analysis import (kpi_summary, build_funnel, monthly_revenue,
                          cohort_analysis, customer_analytics,
                          delivery_analysis, nps_analysis,
                          product_seller_analysis, generate_insights)
    kpis              = kpi_summary(_mf)
    funnel_df, cancel_count, cancel_pct = build_funnel(_mf)
    monthly_rev       = monthly_revenue(_mf)
    cohort_df         = cohort_analysis(_mf)
    cust_df, cust_sum = customer_analytics(_mf)
    delivery_df, by_bucket = delivery_analysis(_mf)
    nps_data, _, _    = nps_analysis(reviews)
    top_products, top_sellers, pf = product_seller_analysis(items, _mf)
    insights = generate_insights(kpis, cust_sum, nps_data, delivery_df, by_bucket)
    return (kpis, funnel_df, cancel_count, cancel_pct, monthly_rev,
            cohort_df, cust_df, cust_sum, delivery_df, by_bucket,
            top_products, top_sellers, pf, insights)

(kpis, funnel_df, cancel_count, cancel_pct, monthly_rev,
 cohort_df, cust_df, cust_sum, delivery_df, by_bucket,
 top_products, top_sellers, pf, insights) = compute(tuple(sel_months + sel_status), mf)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
if page == "📈 Overview":
    st.title("📈 E-Commerce KPI Overview")
    st.caption("Real Olist data — orders, revenue, delivery, satisfaction")

    k1,k2,k3,k4,k5,k6 = st.columns(6)
    k1.metric("Total Orders",    f"{kpis['total_orders']:,}")
    k2.metric("Delivered",       f"{kpis['delivered_orders']:,}", f"{kpis['delivery_rate']}%")
    k3.metric("Canceled",        f"{kpis['canceled_orders']:,}", f"-{kpis['cancel_rate']}%", delta_color="inverse")
    k4.metric("Total Revenue",   f"R${kpis['total_revenue']:,.0f}")
    k5.metric("Avg Order Value", f"R${kpis['avg_order_value']:,.2f}")
    k6.metric("Avg Review",      f"{kpis['avg_review_score']} / 5")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Monthly Revenue")
        fig = px.bar(monthly_rev, x='purchase_month', y='revenue',
                     color_discrete_sequence=[C['blue']],
                     labels={'purchase_month':'Month','revenue':'Revenue (R$)'})
        fig.update_layout(height=300, margin=dict(t=10,b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Monthly Orders")
        fig2 = px.line(monthly_rev, x='purchase_month', y='orders', markers=True,
                       color_discrete_sequence=[C['green']],
                       labels={'purchase_month':'Month','orders':'Orders'})
        fig2.update_layout(height=300, margin=dict(t=10,b=10))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Order Status Distribution")
        status_counts = mf['order_status'].value_counts().reset_index()
        status_counts.columns = ['status','count']
        fig3 = px.pie(status_counts, names='status', values='count', hole=0.45,
                      color_discrete_sequence=list(C.values()))
        fig3.update_layout(height=300, margin=dict(t=10,b=10))
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.subheader("MoM Revenue Growth %")
        mom = monthly_rev.dropna(subset=['mom_growth'])
        fig4 = px.bar(mom, x='purchase_month', y='mom_growth',
                      color='mom_growth',
                      color_continuous_scale='RdYlGn',
                      labels={'purchase_month':'Month','mom_growth':'MoM Growth %'})
        fig4.update_layout(height=300, margin=dict(t=10,b=10))
        st.plotly_chart(fig4, use_container_width=True)

    st.divider()
    st.subheader("💡 Business Insights")
    cols = st.columns(len(insights))
    for col, (kind, msg) in zip(cols, insights):
        getattr(col, kind)(msg)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — ORDER FUNNEL
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔽 Order Funnel":
    st.title("🔽 Order Funnel Analysis")
    st.caption("Real order lifecycle: created → approved → invoiced → processing → shipped → delivered")

    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.subheader("Order Funnel")
        fig = go.Figure(go.Funnel(
            y=funnel_df['stage'],
            x=funnel_df['orders'],
            texttemplate="%{value:,}<br>%{percentInitial:.1%}",
            marker_color=[C['blue'],C['teal'],C['green'],C['orange'],C['purple'],C['red']],
        ))
        fig.update_layout(height=420, margin=dict(t=10,b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Stage Metrics")
        st.dataframe(
            funnel_df.style.format({
                'conversion_rate':'{:.1f}%',
                'dropoff_pct':'{:.1f}%',
                'orders':'{:,}'
            }),
            use_container_width=True, height=420
        )

    st.divider()
    col3, col4, col5 = st.columns(3)
    col3.metric("Delivery Rate",     f"{kpis['delivery_rate']}%")
    col4.metric("Cancellation Rate", f"{kpis['cancel_rate']}%",
                delta=f"{cancel_count:,} orders", delta_color="inverse")
    col5.metric("Biggest Drop-off",
                funnel_df.loc[funnel_df['dropoff_pct'].idxmax(),'stage'],
                f"{funnel_df['dropoff_pct'].max():.1f}% drop")

    st.divider()
    st.subheader("Drop-off % by Stage")
    drop_df = funnel_df[funnel_df['dropoff_pct'] > 0]
    fig5 = px.bar(drop_df, x='stage', y='dropoff_pct',
                  color='dropoff_pct', color_continuous_scale='Reds',
                  text='dropoff_pct',
                  labels={'stage':'Stage','dropoff_pct':'Drop-off %'})
    fig5.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig5.update_layout(height=320, margin=dict(t=10,b=10))
    st.plotly_chart(fig5, use_container_width=True)

    st.divider()
    st.subheader("💡 Funnel Insights")
    max_drop = funnel_df.loc[funnel_df['dropoff_pct'].idxmax()]
    f1, f2, f3 = st.columns(3)
    f1.warning(f"Biggest drop-off at '{max_drop['stage']}': {max_drop['dropoff_pct']:.1f}%")
    f2.error(f"Canceled orders: {cancel_count:,} ({cancel_pct}% of total)")
    f3.success(f"Delivery success rate: {kpis['delivery_rate']}% of all orders")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — COHORT ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔁 Cohort Retention":
    st.title("🔁 Monthly Order Cohort Analysis")
    st.caption("Order volume, avg revenue, review score and late delivery % by month — Olist customer_id is unique per order")

    st.info("ℹ️ Olist's dataset uses a unique customer_id per order (surrogate key). Cohort analysis shows monthly order behavior trends rather than individual customer return rates.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Cohort Months", len(cohort_df))
    col2.metric("Peak Month Orders",   f"{cohort_df['orders'].max():,}")
    col3.metric("Avg Monthly Revenue", f"R${cohort_df['avg_revenue'].mean():,.2f}")

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Monthly Order Volume by Cohort")
        fig = px.bar(cohort_df, x='cohort', y='orders',
                     color='orders', color_continuous_scale='Blues',
                     labels={'cohort':'Month','orders':'Orders'})
        fig.update_layout(height=320, margin=dict(t=10,b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Avg Review Score by Month")
        fig2 = px.line(cohort_df, x='cohort', y='avg_review', markers=True,
                       color_discrete_sequence=[C['green']],
                       labels={'cohort':'Month','avg_review':'Avg Review Score'})
        fig2.add_hline(y=4.0, line_dash='dash', line_color=C['gray'],
                       annotation_text="Target: 4.0")
        fig2.update_layout(height=320, margin=dict(t=10,b=10), yaxis_range=[1,5.5])
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    col_c, col_d = st.columns(2)
    with col_c:
        st.subheader("Avg Order Value by Month")
        fig3 = px.bar(cohort_df, x='cohort', y='avg_revenue',
                      color_discrete_sequence=[C['orange']],
                      labels={'cohort':'Month','avg_revenue':'Avg Order Value (R$)'})
        fig3.update_layout(height=300, margin=dict(t=10,b=10))
        st.plotly_chart(fig3, use_container_width=True)

    with col_d:
        st.subheader("Late Delivery % by Month")
        fig4 = px.bar(cohort_df, x='cohort', y='late_pct',
                      color='late_pct', color_continuous_scale='Reds',
                      labels={'cohort':'Month','late_pct':'Late Delivery %'})
        fig4.update_layout(height=300, margin=dict(t=10,b=10))
        st.plotly_chart(fig4, use_container_width=True)

    st.divider()
    st.subheader("Monthly Cohort Summary Table")
    st.dataframe(cohort_df.style.format({
        'orders':'{:,}', 'avg_revenue':'R${:,.2f}',
        'avg_review':'{:.2f}', 'late_pct':'{:.1f}%'
    }), use_container_width=True)

    st.divider()
    st.subheader("💡 Cohort Insights")
    best_month = cohort_df.loc[cohort_df['orders'].idxmax()]
    worst_rev  = cohort_df.loc[cohort_df['avg_review'].idxmin()]
    r1, r2, r3 = st.columns(3)
    r1.success(f"Peak month: {best_month['cohort']} with {best_month['orders']:,} orders")
    r2.warning(f"Lowest review month: {worst_rev['cohort']} ({worst_rev['avg_review']:.2f}/5) — check delivery issues")
    r3.info(f"Avg order value range: R${cohort_df['avg_revenue'].min():.0f} – R${cohort_df['avg_revenue'].max():.0f}")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — CUSTOMER ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "👥 Customer Analytics":
    st.title("👥 Customer & Order Analytics")
    st.caption("Order value distribution, revenue segments, review segments — delivered orders only")

    st.info("ℹ️ Olist's customer_id is unique per order — each order gets a new ID. Repeat purchase rate cannot be measured from this dataset. All metrics below are order-level.")

    k1,k2,k3 = st.columns(3)
    k1.metric("Total Orders (Delivered)", f"{cust_sum['total_customers']:,}")
    k2.metric("Avg Order Value",          f"R${cust_sum['avg_clv']:,.2f}")
    k3.metric("Avg Review Score",         f"{kpis['avg_review_score']} / 5")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Order Value Distribution")
        clv_data = cust_df['clv'].dropna().clip(upper=cust_df['clv'].quantile(0.95))
        fig = px.histogram(clv_data, nbins=60,
                           color_discrete_sequence=[C['blue']],
                           labels={'value':'Order Value (R$)','count':'Orders','variable':''})
        fig.add_vline(x=cust_sum['avg_clv'], line_dash='dash', line_color=C['red'],
                      annotation_text=f"Avg: R${cust_sum['avg_clv']:.0f}")
        fig.update_layout(height=320, margin=dict(t=10,b=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Revenue Segment Distribution")
        if 'revenue_segment' in cust_df.columns:
            seg_counts = cust_df['revenue_segment'].value_counts().reset_index()
            seg_counts.columns = ['segment','orders']
            fig2 = px.pie(seg_counts, names='segment', values='orders', hole=0.45,
                          color_discrete_sequence=[C['blue'],C['teal'],C['orange'],C['purple']])
            fig2.update_layout(height=320, margin=dict(t=10,b=10))
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Review Segment Distribution")
        if 'review_segment' in cust_df.columns:
            rev_seg = cust_df['review_segment'].value_counts().reset_index()
            rev_seg.columns = ['segment','orders']
            fig3 = px.bar(rev_seg, x='segment', y='orders',
                          color='segment',
                          color_discrete_map={'Promoter':C['green'],'Passive':C['orange'],'Detractor':C['red']},
                          labels={'segment':'Segment','orders':'Orders'})
            fig3.update_layout(height=300, margin=dict(t=10,b=10), showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.subheader("Revenue by Delivery Speed")
        if 'delivery_bucket' in delivery_df.columns and 'revenue' in mf.columns:
            rev_by_speed = (mf[mf['order_status']=='delivered']
                            .merge(delivery_df[['order_id','delivery_bucket']].drop_duplicates(), on='order_id', how='left')
                            .groupby('delivery_bucket')['revenue']
                            .mean().reset_index()
                            .rename(columns={'revenue':'avg_revenue'}))
            bucket_order = ['0-7d','8-14d','15-30d','30d+']
            rev_by_speed['delivery_bucket'] = pd.Categorical(
                rev_by_speed['delivery_bucket'], categories=bucket_order, ordered=True)
            rev_by_speed = rev_by_speed.sort_values('delivery_bucket')
            fig4 = px.bar(rev_by_speed, x='delivery_bucket', y='avg_revenue',
                          color_discrete_sequence=[C['teal']],
                          labels={'delivery_bucket':'Delivery Speed','avg_revenue':'Avg Order Value (R$)'})
            fig4.update_layout(height=300, margin=dict(t=10,b=10))
            st.plotly_chart(fig4, use_container_width=True)

    st.divider()
    st.subheader("💡 Customer Insights")
    c1, c2, c3 = st.columns(3)
    c1.info(f"Avg order value: R${cust_sum['avg_clv']:,.2f} — focus on upsell to grow revenue")
    c2.success(f"Delivery rate: {kpis['delivery_rate']}% — strong fulfillment performance")
    c3.warning(f"Late delivery rate: {kpis['late_delivery_pct']}% — directly impacts review scores")# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — DELIVERY ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🚚 Delivery Analysis":
    st.title("🚚 Delivery Performance Analysis")
    st.caption("Real delivery timestamps — actual vs estimated delivery dates")

    k1,k2,k3 = st.columns(3)
    k1.metric("Avg Delivery Days",  f"{kpis['avg_delivery_days']} days")
    k2.metric("Late Delivery Rate", f"{kpis['late_delivery_pct']}%", delta_color="inverse")
    k3.metric("On-Time Rate",       f"{round(100 - kpis['late_delivery_pct'], 2)}%")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Delivery Time Distribution")
        fig = px.histogram(delivery_df['delivery_days'].dropna(), nbins=60,
                           color_discrete_sequence=[C['blue']],
                           labels={'value':'Delivery Days','count':'Orders'})
        fig.add_vline(x=kpis['avg_delivery_days'], line_dash='dash',
                      line_color=C['red'], annotation_text=f"Avg: {kpis['avg_delivery_days']}d")
        fig.update_layout(height=320, margin=dict(t=10,b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Avg Review Score by Delivery Speed")
        fig2 = px.bar(by_bucket, x='delivery_bucket', y='avg_review',
                      color='avg_review', color_continuous_scale='RdYlGn',
                      text='avg_review',
                      labels={'delivery_bucket':'Delivery Time','avg_review':'Avg Review Score'})
        fig2.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig2.update_layout(height=320, margin=dict(t=10,b=10), yaxis_range=[0,5.5])
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Delay Days Distribution (Late Orders)")
        late_df = delivery_df[delivery_df['delay_days'] > 0]['delay_days']
        fig3 = px.histogram(late_df, nbins=40,
                            color_discrete_sequence=[C['red']],
                            labels={'value':'Days Late','count':'Orders'})
        fig3.update_layout(height=300, margin=dict(t=10,b=10))
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.subheader("Orders by Delivery Bucket")
        fig4 = px.bar(by_bucket, x='delivery_bucket', y='orders',
                      color_discrete_sequence=[C['teal']],
                      text='orders',
                      labels={'delivery_bucket':'Delivery Time','orders':'Orders'})
        fig4.update_traces(texttemplate='%{text:,}', textposition='outside')
        fig4.update_layout(height=300, margin=dict(t=10,b=10))
        st.plotly_chart(fig4, use_container_width=True)

    st.divider()
    st.subheader("💡 Delivery Insights")
    late_score  = delivery_df[delivery_df['is_late']]['review_score'].mean()
    ontime_score= delivery_df[~delivery_df['is_late']]['review_score'].mean()
    d1, d2, d3 = st.columns(3)
    d1.error(f"Late delivery avg review: {late_score:.2f} vs on-time: {ontime_score:.2f} — {ontime_score-late_score:.2f} point gap")
    d2.warning(f"{kpis['late_delivery_pct']}% of orders arrive late — directly hurts NPS")
    d3.info(f"Fastest bucket (0-7d) has highest satisfaction: {by_bucket.iloc[0]['avg_review']:.2f}/5")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — PRODUCTS & SELLERS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📦 Products & Sellers":
    st.title("📦 Products & Seller Analysis")
    st.caption("Revenue concentration, top performers, price vs freight")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top 15 Products by Revenue")
        tp = top_products.copy().reset_index(drop=True)
        tp['label'] = [f"Product #{i+1}" for i in range(len(tp))]
        fig = px.bar(tp, x='revenue', y='label',
                     orientation='h',
                     color='revenue', color_continuous_scale='Blues',
                     text='revenue',
                     labels={'revenue':'Revenue (R$)','label':'Product'})
        fig.update_traces(texttemplate='R$%{text:,.0f}', textposition='outside')
        fig.update_layout(height=480, margin=dict(t=10,b=10),
                          yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Top 15 Sellers by Revenue")
        ts = top_sellers.copy().reset_index(drop=True)
        ts['label'] = [f"Seller #{i+1}" for i in range(len(ts))]
        fig2 = px.bar(ts, x='revenue', y='label',
                      orientation='h',
                      color='revenue', color_continuous_scale='Greens',
                      text='revenue',
                      labels={'revenue':'Revenue (R$)','label':'Seller'})
        fig2.update_traces(texttemplate='R$%{text:,.0f}', textposition='outside')
        fig2.update_layout(height=480, margin=dict(t=10,b=10),
                           yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Price vs Freight Value")
        sample = pf.sample(min(2000, len(pf)), random_state=42)
        fig3 = px.scatter(sample, x='price', y='freight_value',
                          opacity=0.4,
                          color_discrete_sequence=[C['teal']],
                          labels={'price':'Item Price (R$)','freight_value':'Freight (R$)'})
        fig3.update_layout(height=320, margin=dict(t=10,b=10))
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.subheader("Freight as % of Price")
        pf2 = pf.copy()
        pf2['freight_pct'] = (pf2['freight_value'] / pf2['price'] * 100).clip(0, 200)
        fig4 = px.histogram(pf2['freight_pct'], nbins=50,
                            color_discrete_sequence=[C['orange']],
                            labels={'value':'Freight % of Price','count':'Items'})
        fig4.update_layout(height=320, margin=dict(t=10,b=10))
        st.plotly_chart(fig4, use_container_width=True)

    st.divider()
    st.subheader("💡 Product & Seller Insights")
    top_rev_share = top_sellers['revenue'].sum() / items['price'].sum() * 100
    p1, p2, p3 = st.columns(3)
    p1.warning(f"Top 15 sellers account for {top_rev_share:.1f}% of total revenue — high concentration risk")
    p2.info(f"Top product revenue: R${top_products.iloc[0]['revenue']:,.0f} — {top_products.iloc[0]['orders']} orders")
    avg_freight_pct = (pf['freight_value'] / pf['price'] * 100).median()
    p3.info(f"Median freight is {avg_freight_pct:.1f}% of item price — factor into pricing strategy")
