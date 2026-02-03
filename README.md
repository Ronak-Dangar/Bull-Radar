# Bull Radar 🎯

**WhatsApp Group Analytics Dashboard for Bull Agritech**

A Streamlit-based analytics platform to track farmer onboarding and supervisor performance across multiple agricultural centers in Gujarat.

---

## 📋 Overview

Bull Radar helps Bull Agritech track how farmers join WhatsApp groups across different centers and districts. It analyzes WhatsApp chat exports to:

- **Track organic growth** - Farmers who join via group links
- **Monitor manual additions** - Farmers added by supervisors
- **Measure performance** - Compare supervisor and center effectiveness
- **Visualize trends** - Interactive charts showing growth patterns

---

## 🚀 Features

### 1. **Multi-Center Support**
- Pre-configured for 6 districts across Gujarat
- Supports 20+ agricultural centers
- District-wise and center-wise filtering

### 2. **Dual Tracking Mode**
- **Organic Joins**: Automatically detects farmers who join via invite links
- **Manual Additions**: Tracks supervisors who manually add farmers

### 3. **Smart Analytics**
- Real-time KPI dashboard (Total farmers, Organic vs Manual split)
- Interactive time-series charts
- Center performance comparison
- Supervisor leaderboard with ranking

### 4. **Name Mapping**
- Convert phone numbers to supervisor names
- Upload CSV mapping for cleaner reports
- Persistent name database

### 5. **Data Persistence**
- SQLite database for reliable storage
- Duplicate detection (prevents re-counting same joins)
- Historical data retention

---

## 🏗️ Tech Stack

- **Frontend**: Streamlit
- **Database**: SQLite3
- **Visualization**: Plotly Express
- **Data Processing**: Pandas, Regex

---

## 📦 Installation

### Prerequisites
- Python 3.8+
- pip package manager

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/your-repo/bull-radar.git
cd bull-radar
```

2. **Install dependencies**
```bash
pip install streamlit pandas plotly
```

3. **Run the application**
```bash
streamlit run appv3.py
```

The app will open in your browser at `http://localhost:8501`

---

## 📖 Usage Guide

### Step 1: Upload WhatsApp Chat Data

1. Export your WhatsApp group chat:
   - Open WhatsApp group → Menu → More → Export chat → Without media
   - Save the `.txt` file

2. In Bull Radar:
   - Navigate to **"Upload Chat Data"** page
   - Select **District** (e.g., Patan, Kutch, Arvalli)
   - Select **Center** (e.g., Adiya, Adesar, Bayad)
   - Upload the exported `.txt` file
   - Click **"Process Data"**

The app will automatically parse:
- Farmers who joined via link (e.g., "9876543210 joined using a group link")
- Farmers added by supervisors (e.g., "Ramesh added 9988776655")

### Step 2: Map Supervisor Names (Optional)

1. Create a CSV file with two columns:
   ```csv
   Phone,Name
   +919876543210,Ramesh Patel
   9988776655,Suresh Shah
   ```

2. Navigate to **"Map Names (Settings)"**
3. Upload the CSV file
4. Names will now appear instead of phone numbers in reports

### Step 3: View Analytics Dashboard

Navigate to **"Dashboard"** to see:

- **KPI Cards**: Total farmers, organic vs manual breakdown
- **Growth Trend Chart**: Daily join patterns with source split
- **Center Performance**: Stacked bar chart comparing centers
- **Supervisor Leaderboard**: Top performers by manual additions
- **Filters**: Date range, district, and center filters in sidebar

---

## 🗂️ Project Structure

```
├── appv3.py              # Main application (latest version)
├── appv2.py              # Previous version
├── app.py                # Initial prototype
├── bull_radar.db         # SQLite database (auto-generated)
├── README.md             # This file
└── *.txt                 # Sample chat exports (Gujarati centers)
```

---

## 📊 Supported Districts & Centers

| District      | Centers                                              |
|---------------|------------------------------------------------------|
| Patan         | Adiya, Melusan, Madhutra, Satnalpur, Morwada        |
| Kutch         | Adesar, Balasar, Fatehgadh                           |
| Arvalli       | Bayad, Lalsar, Desar                                 |
| Banaskatha    | Thara, Tadav, Sanval, Bhatwad, Kotarwada            |
| Mehsana       | Satalasana                                           |
| Sabarkantha   | Ilol, Deshotar                                       |

*Edit `DISTRICT_MAP` in appv3.py to add more centers*

---

## 🔧 Configuration

### Adding New Centers

Edit the `DISTRICT_MAP` dictionary in `appv3.py`:

```python
DISTRICT_MAP = {
    "YourDistrict": ["Center1", "Center2", "Center3"],
    # ... existing entries
}
```

### Database Schema

**Table: leads**
| Column        | Type     | Description                          |
|---------------|----------|--------------------------------------|
| id            | TEXT     | Unique identifier (PK)               |
| date_time     | DATETIME | When farmer joined                   |
| phone_number  | TEXT     | Farmer's phone number                |
| source_type   | TEXT     | "Organic (Link)" or "Manual Add"     |
| added_by      | TEXT     | Phone/Name of supervisor or "Self"   |
| district      | TEXT     | District name                        |
| center_name   | TEXT     | Center name                          |
| raw_text      | TEXT     | Original WhatsApp message            |

**Table: names_map**
| Column        | Type     | Description                          |
|---------------|----------|--------------------------------------|
| phone_number  | TEXT     | Phone number (PK)                    |
| name          | TEXT     | Supervisor's name                    |

---

## 🐛 Troubleshooting

**Issue: "No new data found"**
- Ensure your WhatsApp export format matches: `MM/DD/YY, HH:MM AM/PM - Message`
- Check that the file contains join/add events

**Issue: Names not showing**
- Verify CSV has `Phone` and `Name` columns (case-insensitive)
- Phone numbers in CSV must exactly match those in chat exports

**Issue: Database locked**
- Close any other instances accessing `bull_radar.db`
- Restart the Streamlit app

---

## 📝 Changelog

### v3 (appv3.py) - Current
- ✅ Name mapping system for supervisor identification
- ✅ Enhanced UI with better filtering
- ✅ Plotly charts for interactive visualization
- ✅ District-level aggregation

### v2 (appv2.py)
- ✅ Added district and center tracking
- ✅ Multi-file upload support

### v1 (app.py)
- ✅ Basic WhatsApp parsing
- ✅ Organic vs Manual tracking

---

## 📄 License

Private project for Bull Agritech internal use.

---

## 👨‍💻 Support

For issues or feature requests, contact the development team at Bull Agritech.

---

## 🙏 Acknowledgments

Built for **Bull Agritech - Sahayog Initiative** to empower agricultural extension teams across Gujarat.
