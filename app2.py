import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Nassau Candy Shipping Route Efficiency",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# DATA LOADING & CACHING
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv('processed_candy_shipping_data.csv')
    df['Order Date'] = pd.to_datetime(df['Order Date'])
    df['Ship Date'] = pd.to_datetime(df['Ship Date'])
    route_kpis = pd.read_csv('route_kpi_summary.csv')
    return df, route_kpis

try:
    df, route_kpis = load_data()
except Exception as e:
    st.error("Error loading data. Please run the Jupyter Notebook preprocessing steps first.")
    st.stop()

# -----------------------------------------------------------------------------
# SIDEBAR FILTERS (USER CAPABILITIES)
# -----------------------------------------------------------------------------
st.sidebar.title("🔍 Filter Controls")

# Date Range Filter
min_date = df['Order Date'].min().date()
max_date = df['Order Date'].max().date()

date_range = st.sidebar.date_input(
    "Select Order Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Region / State Filter
all_regions = sorted(df['Region'].dropna().unique().tolist())
selected_regions = st.sidebar.multiselect("Select Customer Region", all_regions, default=all_regions)

# Ship Mode Filter
all_ship_modes = sorted(df['Ship Mode'].dropna().unique().tolist())
selected_ship_modes = st.sidebar.multiselect("Select Ship Mode", all_ship_modes, default=all_ship_modes)

# Delay Threshold Slider
delay_threshold = st.sidebar.slider(
    "Delay Threshold (Days)",
    min_value=1,
    max_value=14,
    value=4,
    help="Shipments exceeding this lead time will be marked as delayed."
)

# Apply Filters to Main DataFrame
if len(date_range) == 2:
    start_date, end_date = date_range
    filtered_df = df[
        (df['Order Date'].dt.date >= start_date) & 
        (df['Order Date'].dt.date <= end_date) &
        (df['Region'].isin(selected_regions)) &
        (df['Ship Mode'].isin(selected_ship_modes))
    ].copy()
else:
    filtered_df = df[
        (df['Region'].isin(selected_regions)) &
        (df['Ship Mode'].isin(selected_ship_modes))
    ].copy()

# Recalculate Delay Flag based on slider
filtered_df['Is_Delayed'] = filtered_df['Shipping Lead Time'] > delay_threshold

# -----------------------------------------------------------------------------
# APPLICATION HEADER
# -----------------------------------------------------------------------------
st.title("🚚 Factory-to-Customer Shipping Route Efficiency Dashboard")
st.markdown("Logistics performance analysis and route intelligence for **Nassau Candy Distributor**.")

# -----------------------------------------------------------------------------
# TOP METRIC CARDS
# -----------------------------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)

total_orders = len(filtered_df)
avg_lead_time = filtered_df['Shipping Lead Time'].mean() if total_orders > 0 else 0
delayed_orders = filtered_df['Is_Delayed'].sum()
delay_rate = (delayed_orders / total_orders * 100) if total_orders > 0 else 0

m1.metric("Total Shipments", f"{total_orders:,}")
m2.metric("Avg Lead Time", f"{avg_lead_time:.2f} Days")
m3.metric("Delayed Shipments", f"{delayed_orders:,}")
m4.metric("Delay Rate", f"{delay_rate:.1f}%")

st.markdown("---")

# -----------------------------------------------------------------------------
# DASHBOARD MODULES
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Route Efficiency Overview", 
    "🗺️ Geographic Shipping Map", 
    "🚢 Ship Mode Comparison", 
    "🔍 Route Drill-Down"
])

# -----------------------------------------------------------------------------
# MODULE 1: ROUTE EFFICIENCY OVERVIEW
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("Route Performance Leaderboard")
    
    # Dynamic Aggregation
    route_agg = filtered_df.groupby(['Factory', 'State/Province', 'Route']).agg(
        Total_Orders=('Order ID', 'count'),
        Avg_Lead_Time=('Shipping Lead Time', 'mean'),
        Delayed_Count=('Is_Delayed', 'sum')
    ).reset_index()
    
    route_agg['Delay_Rate_%'] = (route_agg['Delayed_Count'] / route_agg['Total_Orders']) * 100

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏆 Top 10 Most Efficient Routes")
        top_10 = route_agg.sort_values(by='Avg_Lead_Time', ascending=True).head(10)
        fig_top = px.bar(
            top_10, 
            x='Avg_Lead_Time', 
            y='Route', 
            orientation='h',
            color='Avg_Lead_Time',
            color_continuous_scale='Greens_r',
            text_auto='.2f',
            labels={'Avg_Lead_Time': 'Avg Lead Time (Days)'}
        )
        fig_top.update_layout(yaxis={'categoryorder': 'total descending'})
        st.plotly_chart(fig_top, use_container_width=True)

    with col2:
        st.markdown("### 🚨 Top 10 Bottleneck Routes")
        bottom_10 = route_agg.sort_values(by='Avg_Lead_Time', ascending=False).head(10)
        fig_bottom = px.bar(
            bottom_10, 
            x='Avg_Lead_Time', 
            y='Route', 
            orientation='h',
            color='Avg_Lead_Time',
            color_continuous_scale='Reds',
            text_auto='.2f',
            labels={'Avg_Lead_Time': 'Avg Lead Time (Days)'}
        )
        fig_bottom.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_bottom, use_container_width=True)

# -----------------------------------------------------------------------------
# MODULE 2: GEOGRAPHIC SHIPPING MAP
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("US Map of Shipping Lead Times & Regional Bottlenecks")
    
    state_perf = filtered_df.groupby('State/Province').agg(
        Avg_Lead_Time=('Shipping Lead Time', 'mean'),
        Total_Orders=('Order ID', 'count')
    ).reset_index()

    fig_map = px.choropleth(
        state_perf,
        locations='State/Province',
        locationmode="USA-states",
        color='Avg_Lead_Time',
        scope="usa",
        color_continuous_scale="YlOrRd",
        hover_data=['Total_Orders', 'Avg_Lead_Time'],
        labels={'Avg_Lead_Time': 'Avg Lead Time (Days)'},
        title="Average Shipping Lead Time by Customer State"
    )
    st.plotly_chart(fig_map, use_container_width=True)

# -----------------------------------------------------------------------------
# MODULE 3: SHIP MODE COMPARISON
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("Shipping Lead Time Comparison by Ship Mode")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        fig_box = px.box(
            filtered_df, 
            x='Ship Mode', 
            y='Shipping Lead Time', 
            color='Ship Mode',
            points="outliers",
            title="Lead Time Variance Across Ship Modes"
        )
        st.plotly_chart(fig_box, use_container_width=True)
        
    with col_b:
        mode_metrics = filtered_df.groupby('Ship Mode').agg(
            Avg_Lead_Time=('Shipping Lead Time', 'mean'),
            Avg_Sales=('Sales', 'mean'),
            Avg_Profit=('Gross Profit', 'mean'),
            Volume=('Order ID', 'count')
        ).reset_index()
        
        fig_mode_bar = px.bar(
            mode_metrics, 
            x='Ship Mode', 
            y='Avg_Lead_Time', 
            color='Ship Mode',
            text_auto='.2f',
            title="Average Days to Ship by Delivery Category"
        )
        st.plotly_chart(fig_mode_bar, use_container_width=True)

# -----------------------------------------------------------------------------
# MODULE 4: ROUTE DRILL-DOWN
# -----------------------------------------------------------------------------
with tab4:
    st.subheader("State-Level & Order-Level Inspection")
    
    selected_state = st.selectbox(
        "Select State for Detailed Drill-Down", 
        sorted(filtered_df['State/Province'].unique())
    )
    
    state_data = filtered_df[filtered_df['State/Province'] == selected_state]
    
    st.markdown(f"### Order Details for **{selected_state}** ({len(state_data)} Orders)")
    
    st.dataframe(
        state_data[[
            'Order ID', 'Order Date', 'Ship Date', 'Factory', 
            'Product Name', 'Ship Mode', 'Shipping Lead Time', 'Is_Delayed', 'Sales', 'Gross Profit'
        ]].sort_values(by='Order Date', ascending=False),
        use_container_width=True
    )