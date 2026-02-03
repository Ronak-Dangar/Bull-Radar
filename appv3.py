import streamlit as st
import re
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, date

# --- CONFIGURATION: DISTRICT -> CENTER MAPPING ---
DISTRICT_MAP = {
    "Patan": ["Adiya", "Melusan", "Madhutra", "Satnalpur", "Morwada"],
    "Kutch": ["Adesar", "Balasar", "Fatehgadh"],
    "Arvalli": ["Bayad", "Lalsar", "Desar"],
    "Banaskatha": ["Thara", "Tadav", "Sanval", "Bhatwad", "Kotarwada"],
    "Mehsana": ["Satalasana"],
    "Sabarkantha": ["Ilol", "Deshotar"]
}

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("bull_radar.db")
    c = conn.cursor()
    
    # Table 1: Leads Data
    c.execute('''CREATE TABLE IF NOT EXISTS leads (
                    id TEXT PRIMARY KEY,
                    date_time DATETIME,
                    phone_number TEXT,
                    source_type TEXT,
                    added_by TEXT,
                    district TEXT,
                    center_name TEXT,
                    raw_text TEXT
                )''')
    
    # Table 2: Phone Number -> Name Mapping
    c.execute('''CREATE TABLE IF NOT EXISTS names_map (
                    phone_number TEXT PRIMARY KEY,
                    name TEXT
                )''')
    
    conn.commit()
    conn.close()

# --- PARSING LOGIC: CHAT FILES ---
def parse_chat_file(file_content, district, center_name):
    timestamp_regex = r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s(\d{1,2}:\d{2}\s?[APap][Mm])"
    new_records = 0
    conn = sqlite3.connect("bull_radar.db")
    c = conn.cursor()
    lines = file_content.split('\n')
    
    for line in lines:
        line = line.strip()
        ts_match = re.match(timestamp_regex, line)
        if not ts_match: continue
            
        date_str, time_str = ts_match.groups()
        try:
            full_ts = datetime.strptime(f"{date_str} {time_str}", "%m/%d/%y %I:%M %p")
        except: continue 

        # 1. Organic Join
        if "joined using a group link" in line or "joined via invite link" in line:
            join_match = re.search(r"-\s(.*?)\sjoined", line)
            if join_match:
                number = join_match.group(1).strip()
                unique_id = f"{full_ts}_{number}_{center_name}"
                try:
                    c.execute("INSERT INTO leads VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                              (unique_id, full_ts, number, "Organic (Link)", "Self", district, center_name, line))
                    new_records += 1
                except sqlite3.IntegrityError: pass 

        # 2. Manual Add
        elif " added " in line:
            add_match = re.search(r"-\s(.*?)\sadded\s(.*)", line)
            if add_match:
                supervisor = add_match.group(1).strip()
                added_people = re.split(r',| and ', add_match.group(2).strip())
                for person in added_people:
                    person = person.strip()
                    if person:
                        unique_id = f"{full_ts}_{person}_{supervisor}_{center_name}"
                        try:
                            c.execute("INSERT INTO leads VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                      (unique_id, full_ts, person, "Manual Add", supervisor, district, center_name, line))
                            new_records += 1
                        except sqlite3.IntegrityError: pass

    conn.commit()
    conn.close()
    return new_records

# --- PARSING LOGIC: NAMES CSV ---
def upload_names_csv(csv_file):
    df = pd.read_csv(csv_file)
    # Expected columns: "Phone", "Name"
    # Normalize headers
    df.columns = [c.lower().strip() for c in df.columns]
    
    if 'phone' not in df.columns or 'name' not in df.columns:
        return 0, "Error: CSV must have 'Phone' and 'Name' columns."
    
    conn = sqlite3.connect("bull_radar.db")
    c = conn.cursor()
    count = 0
    for _, row in df.iterrows():
        # Clean phone number logic could go here
        phone = str(row['phone']).strip()
        name = str(row['name']).strip()
        try:
            c.execute("INSERT OR REPLACE INTO names_map VALUES (?, ?)", (phone, name))
            count += 1
        except: pass
    conn.commit()
    conn.close()
    return count, "Success"

# --- MAIN APP UI ---
st.set_page_config(page_title="Bull Radar", layout="wide", initial_sidebar_state="expanded")

# CUSTOM CSS FOR LIGHT THEME & BRANDING
st.markdown("""
    <style>
    .main { background-color: #FFFFFF; }
    h1, h2, h3 { color: #2C3E50; }
    .stMetric { background-color: #F0F2F6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

init_db()

# SIDEBAR NAVIGATION
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2504/2504936.png", width=50) # Placeholder Icon
st.sidebar.title("Bull Radar 🎯")
page = st.sidebar.radio("Navigation", ["Dashboard", "Upload Chat Data", "Map Names (Settings)"])

# --- PAGE 1: UPLOAD CHAT DATA ---
if page == "Upload Chat Data":
    st.header("📂 Upload Center Data")
    col1, col2 = st.columns(2)
    with col1:
        s_district = st.selectbox("1. Select District:", list(DISTRICT_MAP.keys()))
    with col2:
        s_center = st.selectbox("2. Select Center:", DISTRICT_MAP[s_district])
    
    uploaded_file = st.file_uploader(f"Upload Chat Export for {s_center}", type="txt")
    if uploaded_file and st.button("Process Data"):
        content = uploaded_file.read().decode("utf-8")
        with st.spinner("Analyzing..."):
            count = parse_chat_file(content, s_district, s_center)
        if count > 0:
            st.success(f"✅ Captured {count} new leads for **{s_center}**")
        else:
            st.warning("⚠️ No new data found.")

# --- PAGE 2: MAP NAMES ---
elif page == "Map Names (Settings)":
    st.header("👤 Supervisor Name Mapping")
    st.info("Upload a CSV with two columns: `Phone` and `Name`. This will replace numbers with names in the dashboard.")
    
    name_file = st.file_uploader("Upload Names CSV", type="csv")
    if name_file:
        count, msg = upload_names_csv(name_file)
        if count > 0:
            st.success(f"✅ Successfully mapped {count} phone numbers to names!")
        else:
            st.error(msg)
            
    # Show current mappings
    conn = sqlite3.connect("bull_radar.db")
    mapping_df = pd.read_sql_query("SELECT * FROM names_map", conn)
    conn.close()
    if not mapping_df.empty:
        st.subheader("Current Mappings")
        st.dataframe(mapping_df, hide_index=True)

# --- PAGE 3: DASHBOARD ---
elif page == "Dashboard":
    st.title("📊 Bull Radar Analytics")
    
    # 1. LOAD DATA & MERGE NAMES
    conn = sqlite3.connect("bull_radar.db")
    df = pd.read_sql_query("SELECT * FROM leads", conn)
    names_df = pd.read_sql_query("SELECT * FROM names_map", conn)
    conn.close()
    
    if not df.empty:
        df['date_time'] = pd.to_datetime(df['date_time'])
        df['date_only'] = df['date_time'].dt.date

        # MERGE: Replace 'added_by' number with Name if it exists
        if not names_df.empty:
            # We treat 'phone_number' in names_map as the join key
            # Standardize format if needed (remove spaces, etc in future)
            mapping_dict = dict(zip(names_df.phone_number, names_df.name))
            df['added_by_name'] = df['added_by'].map(mapping_dict).fillna(df['added_by'])
        else:
            df['added_by_name'] = df['added_by']

        # --- FILTERS SIDEBAR ---
        st.sidebar.divider()
        st.sidebar.header("🔍 Filters")
        
        # DATE FILTER
        min_date = df['date_only'].min()
        max_date = df['date_only'].max()
        
        date_range = st.sidebar.date_input("Select Date Range", [min_date, max_date])
        if len(date_range) == 2:
            start_date, end_date = date_range
            df = df[(df['date_only'] >= start_date) & (df['date_only'] <= end_date)]
        
        # LOCATION FILTERS
        sel_dist = st.sidebar.selectbox("Filter District", ["All"] + list(df['district'].unique()))
        if sel_dist != "All":
            df = df[df['district'] == sel_dist]
            
        sel_cent = st.sidebar.selectbox("Filter Center", ["All"] + list(df['center_name'].unique()))
        if sel_cent != "All":
            df = df[df['center_name'] == sel_cent]

        # --- KPI ROW ---
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Farmers", len(df))
        kpi2.metric("Organic Joins", len(df[df['source_type'] == "Organic (Link)"]))
        kpi3.metric("Manual Adds", len(df[df['source_type'] == "Manual Add"]))
        
        # Calculate Top Day
        if not df.empty:
            top_day = df['date_only'].value_counts().idxmax()
            kpi4.metric("Peak Growth Day", str(top_day))

        st.divider()

        # --- CHARTS ---
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("📈 Organic vs Manual Trend")
            timeline = df.groupby(['date_only', 'source_type']).size().reset_index(name='Count')
            fig_time = px.line(timeline, x='date_only', y='Count', color='source_type', 
                               markers=True, color_discrete_sequence=['#2ecc71', '#e74c3c'])
            fig_time.update_layout(xaxis_title="Date", yaxis_title="Farmers Joined")
            st.plotly_chart(fig_time, use_container_width=True)
            
        with col_right:
            st.subheader("📍 Center Performance")
            center_perf = df.groupby('center_name')['source_type'].value_counts().unstack().fillna(0)
            fig_bar = px.bar(center_perf, barmode='stack', 
                             color_discrete_sequence=['#e74c3c', '#2ecc71']) # Manual=Red, Organic=Green (Auto mapped)
            st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()

        # --- SUPERVISOR LEADERBOARD (WITH NAMES) ---
        st.subheader("🏆 Top Supervisors (Manual Additions)")
        
        manual_df = df[df['source_type'] == "Manual Add"]
        if not manual_df.empty:
            # Group by NAME instead of number
            sup_stats = manual_df.groupby(['added_by_name', 'center_name']).size().reset_index(name='Farmers Added')
            sup_stats = sup_stats.sort_values(by='Farmers Added', ascending=False).head(15)
            
            fig_sup = px.bar(sup_stats, x='Farmers Added', y='added_by_name', color='center_name', 
                             orientation='h', title="Top 15 Supervisors", text_auto=True)
            fig_sup.update_layout(yaxis_title="Supervisor Name")
            st.plotly_chart(fig_sup, use_container_width=True)
            
            with st.expander("View Detailed Data Table"):
                st.dataframe(manual_df[['date_time', 'phone_number', 'added_by_name', 'center_name', 'raw_text']], use_container_width=True)
        else:
            st.info("No manual additions in this filtered view.")

    else:
        st.info("👋 Welcome to Bull Radar! Go to 'Upload Chat Data' to import your first file.")