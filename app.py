import streamlit as st
import re
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("bull_agritech.db")
    c = conn.cursor()
    # We create a table with a UNIQUE constraint to prevent duplicate entries
    # if you upload the same chat file next week.
    c.execute('''CREATE TABLE IF NOT EXISTS leads (
                    id TEXT PRIMARY KEY,
                    date_time DATETIME,
                    phone_number TEXT,
                    source_type TEXT,
                    added_by TEXT,
                    raw_text TEXT
                )''')
    conn.commit()
    conn.close()

# --- PARSING LOGIC ---
def parse_chat_file(file_content):
    # Regex Patterns
    # Note: \u202f handles the narrow non-breaking space used in some WhatsApp exports
    timestamp_regex = r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s(\d{1,2}:\d{2}\s?[APap][Mm])"
    
    new_records = 0
    conn = sqlite3.connect("bull_agritech.db")
    c = conn.cursor()

    lines = file_content.split('\n')
    
    for line in lines:
        line = line.strip()
        # 1. Extract Timestamp
        ts_match = re.match(timestamp_regex, line)
        if not ts_match:
            continue
            
        date_str, time_str = ts_match.groups()
        # Normalize date format for sorting
        try:
            full_ts = datetime.strptime(f"{date_str} {time_str}", "%m/%d/%y %I:%M %p")
        except:
            continue # Skip malformed dates

        # 2. CHECK: Organic Join
        if "joined using a group link" in line:
            # Extract the number
            join_match = re.search(r"-\s(.*?)\sjoined using a group link", line)
            if join_match:
                number = join_match.group(1).strip()
                # Create a unique ID for this event (Date + Number) to avoid duplicates
                unique_id = f"{full_ts}_{number}_organic"
                
                try:
                    c.execute("INSERT INTO leads VALUES (?, ?, ?, ?, ?, ?)",
                              (unique_id, full_ts, number, "Organic (Link)", "Self", line))
                    new_records += 1
                except sqlite3.IntegrityError:
                    pass # Already exists, ignore

        # 3. CHECK: Supervisor Added Someone
        elif " added " in line:
            add_match = re.search(r"-\s(.*?)\sadded\s(.*)", line)
            if add_match:
                supervisor = add_match.group(1).strip()
                added_people_str = add_match.group(2).strip()
                
                # Handle "User A added User B and User C"
                # This is a basic split, typically WhatsApp uses commas or 'and'
                # For accurate counting, we split by common separators
                people_list = re.split(r',| and ', added_people_str)
                
                for person in people_list:
                    person = person.strip()
                    if person:
                        unique_id = f"{full_ts}_{person}_added_{supervisor}"
                        try:
                            c.execute("INSERT INTO leads VALUES (?, ?, ?, ?, ?, ?)",
                                      (unique_id, full_ts, person, "Manual Add", supervisor, line))
                            new_records += 1
                        except sqlite3.IntegrityError:
                            pass

    conn.commit()
    conn.close()
    return new_records

# --- DASHBOARD UI ---
st.set_page_config(page_title="Bull Agritech Tracker", layout="wide")
st.title("🚜 Bull Agritech: Group Growth Dashboard")

# 1. Initialize DB
init_db()

# 2. File Uploader
uploaded_file = st.file_uploader("Upload WhatsApp Chat Export (.txt)", type="txt")

if uploaded_file is not None:
    # Read and decode the file
    content = uploaded_file.read().decode("utf-8")
    
    with st.spinner('Processing Chat File...'):
        count = parse_chat_file(content)
    
    if count > 0:
        st.success(f"✅ Successfully added {count} new records to database!")
    else:
        st.warning("⚠️ No new records found (or duplicates skipped).")

# 3. Load Data for Analysis
conn = sqlite3.connect("bull_agritech.db")
df = pd.read_sql_query("SELECT * FROM leads", conn)
conn.close()

if not df.empty:
    df['date_time'] = pd.to_datetime(df['date_time'])
    
    # --- METRICS ROW ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Farmers Tracked", len(df))
    col2.metric("Organic (Link) Joins", len(df[df['source_type'] == "Organic (Link)"]))
    col3.metric("Manual Adds", len(df[df['source_type'] == "Manual Add"]))

    st.divider()

    # --- TAB 1: SUPERVISOR PERFORMANCE ---
    st.header("🏆 Supervisor Performance")
    
    # Filter only manual adds
    manual_df = df[df['source_type'] == "Manual Add"]
    
    if not manual_df.empty:
        # Count adds by Supervisor
        supervisor_counts = manual_df['added_by'].value_counts().reset_index()
        supervisor_counts.columns = ['Supervisor', 'Farmers Added']
        
        st.bar_chart(supervisor_counts.set_index('Supervisor'))
        
        st.dataframe(supervisor_counts, use_container_width=True)
    else:
        st.info("No manual adds found yet.")

    st.divider()

    # --- TAB 2: GROWTH OVER TIME ---
    st.header("📈 Growth Timeline")
    
    # Group by Date and Source Type
    timeline_df = df.groupby([df['date_time'].dt.date, 'source_type']).size().unstack(fill_value=0)
    
    st.line_chart(timeline_df)

    # --- TAB 3: RAW DATA ---
    with st.expander("View Raw Data"):
        st.dataframe(df.sort_values(by='date_time', ascending=False))

else:
    st.info("Database is empty. Please upload a chat file to begin.")