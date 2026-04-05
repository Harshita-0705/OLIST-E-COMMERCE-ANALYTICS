# Power BI Dashboard — Design Plan & DAX Formulas
## Product Analytics & KPI Intelligence System

---

## Dashboard Structure (6 Pages)

### Page 1 — Overview (KPIs)
**Visuals:** KPI cards, Area chart (MAU), Bar chart (Revenue), Donut (Channels), Bar (Plan types)

### Page 2 — Funnel
**Visuals:** Funnel chart, Table (stage metrics), Bar (drop-off %), Segmented bar (by device/country)

### Page 3 — Retention
**Visuals:** Matrix heatmap (cohort), Line chart (retention curve), Bar (returning users %)

### Page 4 — Feature Adoption
**Visuals:** Horizontal bar (top features), Diverging bar (retention lift), Line (usage trend)

### Page 5 — Experiments
**Visuals:** Clustered bar (control vs variant), KPI cards (lift, p-value), Table (results)

### Page 6 — Churn & Segments
**Visuals:** Bar (churn by segment), Donut (churned vs active), Histogram (days inactive)

---

## Data Model (Star Schema)

```
events (fact)
  ├── users (dim)       — user_id
  ├── sessions (dim)    — session_id
  ├── features (dim)    — feature_name
  └── orders (fact)     — user_id
```

---

## DAX Measures

### Core KPIs

```dax
-- Total Users
Total Users = DISTINCTCOUNT(users[user_id])

-- Daily Active Users (DAU)
DAU =
CALCULATE(
    DISTINCTCOUNT(events[user_id]),
    FILTER(events, events[timestamp] = MAX(events[timestamp]))
)

-- Monthly Active Users (MAU)
MAU =
CALCULATE(
    DISTINCTCOUNT(events[user_id]),
    DATESMTD(events[timestamp])
)

-- DAU/MAU Stickiness Ratio
Stickiness % =
DIVIDE([DAU], [MAU]) * 100

-- Total Revenue
Total Revenue =
CALCULATE(
    SUM(orders[amount]),
    orders[status] = "delivered"
)

-- ARPU (Average Revenue Per User)
ARPU =
DIVIDE(
    CALCULATE(SUM(orders[amount]), orders[status] = "delivered"),
    DISTINCTCOUNT(orders[user_id])
)

-- MoM Revenue Growth
MoM Revenue Growth % =
VAR CurrentMonth = [Total Revenue]
VAR PrevMonth =
    CALCULATE(
        SUM(orders[amount]),
        DATEADD(orders[order_date], -1, MONTH),
        orders[status] = "delivered"
    )
RETURN
    DIVIDE(CurrentMonth - PrevMonth, PrevMonth) * 100
```

### Funnel Measures

```dax
-- Signup Count
Signups =
CALCULATE(DISTINCTCOUNT(events[user_id]), events[event_type] = "signup")

-- Activation Rate (feature use within 7 days of signup)
Activation Rate % =
VAR ActivatedUsers =
    CALCULATE(
        DISTINCTCOUNT(events[user_id]),
        events[event_type] = "feature_use"
    )
RETURN DIVIDE(ActivatedUsers, [Signups]) * 100

-- Conversion Rate (signup → purchase)
Conversion Rate % =
VAR Converted =
    CALCULATE(DISTINCTCOUNT(events[user_id]), events[event_type] = "purchase")
RETURN DIVIDE(Converted, [Signups]) * 100

-- Drop-off % between stages
Dropoff % =
VAR CurrentStage = SELECTEDVALUE(funnel_stages[users])
VAR PrevStage    = CALCULATE(MAX(funnel_stages[users]),
                             FILTER(funnel_stages, funnel_stages[order] = MAX(funnel_stages[order]) - 1))
RETURN (1 - DIVIDE(CurrentStage, PrevStage)) * 100
```

### Retention Measures

```dax
-- Day-7 Retention
Day7 Retention % =
VAR Day7Users =
    CALCULATE(
        DISTINCTCOUNT(events[user_id]),
        FILTER(events,
            DATEDIFF(
                RELATED(users[signup_date]),
                events[timestamp], DAY
            ) BETWEEN 7 AND 13
        )
    )
RETURN DIVIDE(Day7Users, [Total Users]) * 100

-- Day-30 Retention
Day30 Retention % =
VAR Day30Users =
    CALCULATE(
        DISTINCTCOUNT(events[user_id]),
        FILTER(events,
            DATEDIFF(
                RELATED(users[signup_date]),
                events[timestamp], DAY
            ) BETWEEN 30 AND 36
        )
    )
RETURN DIVIDE(Day30Users, [Total Users]) * 100

-- Cohort Retention Rate
Cohort Retention % =
VAR CohortSize =
    CALCULATE(
        DISTINCTCOUNT(users[user_id]),
        FILTER(users,
            FORMAT(users[signup_date], "YYYY-MM") = SELECTEDVALUE(cohort_table[cohort])
        )
    )
VAR ActiveInMonth =
    CALCULATE(
        DISTINCTCOUNT(events[user_id]),
        FILTER(events,
            FORMAT(events[timestamp], "YYYY-MM") = SELECTEDVALUE(cohort_table[activity_month])
        )
    )
RETURN DIVIDE(ActiveInMonth, CohortSize) * 100
```

### Churn Measures

```dax
-- Churn Rate
Churn Rate % =
VAR LastDate = MAX(events[timestamp])
VAR ChurnedUsers =
    CALCULATE(
        DISTINCTCOUNT(users[user_id]),
        FILTER(users,
            DATEDIFF(
                CALCULATE(MAX(events[timestamp]), ALLEXCEPT(events, events[user_id])),
                LastDate, DAY
            ) >= 30
        )
    )
RETURN DIVIDE(ChurnedUsers, [Total Users]) * 100

-- At-Risk Users (20–29 days inactive)
At Risk Users =
VAR LastDate = MAX(events[timestamp])
RETURN
    CALCULATE(
        DISTINCTCOUNT(users[user_id]),
        FILTER(users,
            VAR DaysInactive =
                DATEDIFF(
                    CALCULATE(MAX(events[timestamp]), ALLEXCEPT(events, events[user_id])),
                    LastDate, DAY
                )
            RETURN DaysInactive >= 20 && DaysInactive < 30
        )
    )
```

### A/B Experiment Measures

```dax
-- Conversion Rate by Experiment Group
Experiment Conversion % =
CALCULATE(
    DIVIDE(
        DISTINCTCOUNT(events[user_id]),
        CALCULATE(DISTINCTCOUNT(users[user_id]))
    ) * 100,
    events[event_type] = "purchase"
)

-- Conversion Lift (Variant vs Control)
Conversion Lift % =
VAR VariantRate =
    CALCULATE([Experiment Conversion %], users[experiment_group] = "variant")
VAR ControlRate =
    CALCULATE([Experiment Conversion %], users[experiment_group] = "control")
RETURN DIVIDE(VariantRate - ControlRate, ControlRate) * 100
```

### Feature Adoption Measures

```dax
-- Feature Adoption Rate
Feature Adoption % =
DIVIDE(
    CALCULATE(DISTINCTCOUNT(events[user_id]), events[event_type] = "feature_use"),
    [Total Users]
) * 100

-- Events per User (engagement depth)
Events Per User =
DIVIDE(
    CALCULATE(COUNT(events[event_id]), events[event_type] = "feature_use"),
    CALCULATE(DISTINCTCOUNT(events[user_id]), events[event_type] = "feature_use")
)
```

---

## Power BI Import Steps

1. Open Power BI Desktop
2. Get Data → Text/CSV → import all files from `data/` folder
3. Build relationships in Model view (star schema above)
4. Create a Date table:
   ```dax
   DateTable = CALENDAR(DATE(2023,1,1), DATE(2024,12,31))
   ```
5. Mark DateTable as Date Table
6. Paste DAX measures into each page
7. Import PNG charts from `charts_output/` as Image visuals for quick wins

---

## Business Insights (Pre-built Narrative)

| Insight | Signal | Action |
|---|---|---|
| Biggest funnel drop at Activation | < 40% activate within 7 days | Improve onboarding flow |
| Free plan has highest churn | 2x churn vs paid plans | Add upgrade nudge at day 7 |
| `checkout` feature drives +15pp retention | Users who checkout retain better | Surface checkout earlier in UX |
| Variant shows positive lift | A/B test result | Roll out variant if p < 0.05 |
| DAU/MAU < 20% | Low stickiness | Add daily value hooks (notifications, dashboard) |
| Mobile conversion lower than desktop | Device gap | Optimize mobile checkout flow |
