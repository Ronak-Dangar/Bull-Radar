import streamlit as st
import re
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION: DISTRICT -> CENTER MAPPING ---
DISTRICT_MAP = {
    "Patan": ["Adiya", "Melusan", "Madhutra", "Satnalpur", "Morwada"],
    "Kutch": ["Adesar", "Balasar", "Fatehgadh"],
    "Arvalli": ["Bayad", "Lalsar", "Desar"],
    "Banaskatha": ["Thara", "Tadav", "Sanval", "Bhatwad", "Kotarwada"],
    "Mehsana": ["Satalasana"],
    "Sabarkantha": ["Ilol", "Deshotar"]
}

# Flatten list for validation if needed
ALL_CENTERS = [center for centers in DISTRICT_MAP.values() for center in centers]

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("bull_agritech_v3.db")
    c = conn.cursor()
    # Added 'district' column
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
    conn.commit()
    conn.close()

# --- PARSING LOGIC ---
def parse_chat_file(file_content, district, center_name):
    # Regex to handle multiple date formats (e.g. 8/4/25, 08/04/2025)
    timestamp_regex = r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s(\d{1,2}:\d{2}\s?[APap][Mm])"
    
    new_records = 0
    conn = sqlite3.connect("bull_agritech_v3.db")
    c = conn.cursor()

    lines = file_content.split('\n')
    
    for line in lines:
        line = line.strip()
        # 1. Extract Timestamp
        ts_match = re.match(timestamp_regex, line)
        if not ts_match:
            continue
            
        date_str, time_str = ts_match.groups()
        try:
            full_ts = datetime.strptime(f"{date_str} {time_str}", "%m/%d/%y %I:%M %p")
        except:
            continue 

        # 2. CHECK: Organic Join (Link)
        if "joined using a group link" in line or "joined via invite link" in line:
            join_match = re.search(r"-\s(.*?)\sjoined", line)
            if join_match:
                number = join_match.group(1).strip()
                # Unique ID: Time + Number + Center
                unique_id = f"{full_ts}_{number}_{center_name}"
                
                try:
                    c.execute("INSERT INTO leads VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                              (unique_id, full_ts, number, "Organic (Link)", "Self", district, center_name, line))
                    new_records += 1
                except sqlite3.IntegrityError:
                    pass 

        # 3. CHECK: Supervisor Added Someone
        elif " added " in line:
            add_match = re.search(r"-\s(.*?)\sadded\s(.*)", line)
            if add_match:
                supervisor = add_match.group(1).strip()
                added_people_str = add_match.group(2).strip()
                
                # Split multiple adds
                people_list = re.split(r',| and ', added_people_str)
                
                for person in people_list:
                    person = person.strip()
                    if person:
                        unique_id = f"{full_ts}_{person}_{supervisor}_{center_name}"
                        try:
                            c.execute("INSERT INTO leads VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                      (unique_id, full_ts, person, "Manual Add", supervisor, district, center_name, line))
                            new_records += 1
                        except sqlite3.IntegrityError:
                            pass

    conn.commit()
    conn.close()
    return new_records

# --- MAIN APP UI ---
st.set_page_config(page_title="Bull Agritech Tracker", layout="wide")
init_db()

# SIDEBAR
page = st.sidebar.radio("Go to", ["Dashboard", "Upload New Data"])

if page == "Upload New Data":
    st.header("📂 Upload Center Data")
    st.info("Follow the hierarchy: Select District -> Select Center -> Upload File")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Step 1: Select District
        selected_district = st.selectbox("1. Select District:", list(DISTRICT_MAP.keys()))
    
    with col2:
        # Step 2: Select Center (Filtered based on District)
        available_centers = DISTRICT_MAP[selected_district]
        selected_center = st.selectbox("2. Select Center:", available_centers)
    
    # Step 3: File Uploader
    uploaded_file = st.file_uploader(f"Upload Chat Export for {selected_center}", type="txt")
    
    if uploaded_file and st.button("Process File"):
        content = uploaded_file.read().decode("utf-8")
        with st.spinner(f"Processing data for {selected_center}..."):
            count = parse_chat_file(content, selected_district, selected_center)
        
        if count > 0:
            st.success(f"✅ Successfully added {count} new leads to **{selected_center} ({selected_district})**!")
        else:
            st.warning("⚠️ No new data found (this file might have been uploaded already).")

elif page == "Dashboard":
    st.title("🚜 Bull Agritech: Network Analytics")
    
    conn = sqlite3.connect("bull_agritech_v3.db")
    df = pd.read_sql_query("SELECT * FROM leads", conn)
    conn.close()
    
    if not df.empty:
        df['date_time'] = pd.to_datetime(df['date_time'])
        
        # --- FILTERS ---
        st.sidebar.header("Filters")
        
        # District Filter
        all_districts = ["All"] + list(df['district'].unique())
        district_filter = st.sidebar.selectbox("Filter by District", all_districts)
        
        # Apply District Filter
        if district_filter != "All":
            df = df[df['district'] == district_filter]
            
        # Center Filter (Dynamic based on District)
        all_centers_in_df = ["All"] + list(df['center_name'].unique())
        center_filter = st.sidebar.selectbox("Filter by Center", all_centers_in_df)
        
        # Apply Center Filter
        if center_filter != "All":
            df = df[df['center_name'] == center_filter]

        # --- KPI ROW ---
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Farmers Tracked", len(df))
        
        organic_df = df[df['source_type'] == "Organic (Link)"]
        manual_df = df[df['source_type'] == "Manual Add"]
        
        kpi2.metric("Organic Joins (Link)", len(organic_df))
        kpi3.metric("Manual Adds (Supervisors)", len(manual_df))
        
        # Calculate % Organic
        if len(df) > 0:
            perc_organic = (len(organic_df) / len(df)) * 100
            kpi4.metric("Organic %", f"{perc_organic:.1f}%")
        
        st.divider()

        # --- CHARTS ROW 1 ---
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("📍 Performance by District")
            dist_counts = df.groupby(['district', 'source_type']).size().reset_index(name='Count')
            fig_dist = px.bar(dist_counts, x='district', y='Count', color='source_type', 
                              title="District Wise Breakdown", barmode='group')
            st.plotly_chart(fig_dist, use_container_width=True)

        with col_right:
            st.subheader("📈 Growth Timeline")
            # Resample by Week 'W' or Day 'D'
            timeline = df.set_index('date_time').resample('W').size().reset_index(name='New Leads')
            fig_line = px.line(timeline, x='date_time', y='New Leads', markers=True, 
                               title="Weekly Growth Trend")
            st.plotly_chart(fig_line, use_container_width=True)

        st.divider()
        
        # --- SUPERVISOR SECTION ---
        st.subheader("🏆 Top Supervisors (Manual Additions)")
        
        if not manual_df.empty:
            sup_stats = manual_df.groupby(['added_by', 'district', 'center_name']).size().reset_index(name='Total Adds')
            sup_stats = sup_stats.sort_values(by='Total Adds', ascending=False).head(15)
            
            # Show a nice table or bar chart
            st.dataframe(sup_stats, use_container_width=True)
            
            fig_sup = px.bar(sup_stats, x='Total Adds', y='added_by', color='district', 
                             orientation='h', title="Top 15 Supervisors by Output")
            st.plotly_chart(fig_sup, use_container_width=True)
        else:
            st.info("No manual addition data found for the selected filters.")

    else:
        st.info("Database is empty. Please go to 'Upload New Data' to add your first file.")