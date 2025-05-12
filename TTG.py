import streamlit as st
import pandas as pd
import random
import os
import io
from PIL import Image
from datetime import datetime, timedelta

# --- Streamlit UI Configuration ---
st.set_page_config(page_title="Timetable Generator", layout="wide")

st.markdown("""
    <style>
        /* Glossy light blue background for main container */
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, rgba(173, 216, 230, 0.6), rgba(224, 255, 255, 0.8));
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            padding: 2rem;
        }

        /* Style content blocks */
        .block-container {
            background: rgba(255, 255, 255, 0.7);
            border-radius: 16px;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
            padding: 2rem;
        }

        /* Widgets: inputs and selects */
        .stTextInput > div > input,
        .stNumberInput > div > input,
        .stSelectbox > div,
        .stTextArea > div > textarea {
            background-color: rgba(240, 248, 255, 0.85) !important;
            border-radius: 8px !important;
            border: 1px solid #b0c4de !important;
        }

        /* Buttons */
        button[kind="primary"] {
            background-color: #4682B4 !important;
            color: white !important;
            border-radius: 10px !important;
            padding: 10px 16px !important;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }

        button[kind="primary"]:hover {
            background-color: #5B9BD5 !important;
        }

        /* Shadow for all input widgets and select boxes */
        .stTextInput, .stNumberInput, .stSelectbox, .stTimeInput, .stRadio {
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1) !important;
            border-radius: 8px !important;
            padding: 4px !important;
        }

        /* Bold section headings */
        h3, h4 {
            font-weight: bold !important;
            color: #003366 !important;
        }

        /* Bold subject labels (TH/PR section inputs) */
        label[for^="custom_sub_"],
        label[for$="_th"],
        label[for$="_pr"] {
            font-weight: bold !important;
            color: #000066 !important;
        }

        /* Extra: Bold common label containers used by Streamlit */
        .stTextInput label,
        .stNumberInput label,
        .stSelectbox label,
        .stTextArea label,
        div[data-testid="stFormLabel"],
        div.css-1r6slb0 p,    /* Covers extra <p> styled labels */
        div.css-1544g2n,      /* Some inline label containers */
        div[data-testid="stMarkdownContainer"] > p {
            font-weight: bold !important;
        }
    </style>
""", unsafe_allow_html=True)


# --- UI Inputs for Configurations ---
st.sidebar.header("📍 Configuration")
# --- Institution Type Selection ---
st.sidebar.header("💡 Start Here")
institution_type = st.sidebar.selectbox(
    " Select Institution Type",
    ["", "📚School", "🧪Coaching Institute", "🏛️College"]
)

if institution_type == "":
    st.warning("🥇PLEASE SELECT THE TYPE OF INSTITUTION TO PROCEED.")
    st.stop()
uploaded_logo = st.sidebar.file_uploader("Upload Institute Logo", type=["png", "jpg", "jpeg"])
uploaded_excel = st.sidebar.file_uploader("Upload Excel File", type=["xlsx"])
institute_name = st.sidebar.text_input("Institute Name", "Step to Success Higher Secondary School")

# --- Fallback paths (optional) ---
if uploaded_logo is not None:
    logo_path = uploaded_logo
elif os.path.exists("school-logo.png"):
    logo_path = "school-logo.png"
else:
    logo_path = None

if uploaded_excel is not None:
    excel_path = uploaded_excel
else:
    st.error("Please upload a valid Excel file to proceed.")
    st.stop()

def expand_class_subject_allocation(df):
    rows = []
    for _, row in df.iterrows():
        classes = [c.strip() for c in str(row['Class']).split(',')]
        for cls in classes:
            rows.append({'Class': cls, 'Subject': row['Subject']})
    return pd.DataFrame(rows)


# --- Top Header: Logo + Title ---
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if logo_path:
        st.image(logo_path, width=100)
    else:
        st.warning("Logo not found or not uploaded.")
with col_title:
    st.markdown(f"# {institute_name}")
    st.markdown("## 📜Class Timetable Generator")

# --- Load teacher-subject mapping from Excel ---
@st.cache_data
def load_excel_data(file_path, institution_type):
    xls = pd.ExcelFile(file_path)

    if institution_type == "📚School":
        df_mapping = pd.read_excel(xls, sheet_name="TeacherMapping")
        df_subject_hours_raw = pd.read_excel(xls, sheet_name="CLASS-SUBJECT ALLOCATION")
        df_subject_hours_raw.columns = df_subject_hours_raw.columns.str.strip()  # Clean headers
        df_subject_hours = expand_class_subject_allocation(df_subject_hours_raw)

        df_classes = pd.read_excel(xls, sheet_name="Classes")

    elif institution_type == "🧪Coaching Institute":
        df_mapping = pd.read_excel(xls, sheet_name="FACULTY-SUBJECT")
        df_mapping['Teachers'] = df_mapping['Faculty']
        df_subject_hours_raw = pd.read_excel(xls, sheet_name="SUBJECTS_COACHING")
        df_subject_hours_raw.columns = df_subject_hours_raw.columns.str.strip()
        df_subject_hours_raw.rename(columns={'Stream': 'Class'}, inplace=True)  # Fix here
        df_subject_hours = expand_class_subject_allocation(df_subject_hours_raw)
        df_classes = pd.DataFrame({'Class': df_subject_hours['Class'].unique()})
        df_subjects_coaching = pd.read_excel(excel_path, sheet_name="SUBJECTS_COACHING")
        df_subjects_coaching.columns = df_subjects_coaching.columns.str.strip()
        df_subjects_coaching.rename(columns={'Stream': 'Class'}, inplace=True)

        stream_subject_map = df_subjects_coaching.groupby('Class')['Subject'].apply(list).to_dict()
        # --- Build subject_faculty_map from FACULTY-SUBJECT ---
        df_faculty = pd.read_excel(excel_path, sheet_name="FACULTY-SUBJECT")
        df_faculty.columns = df_faculty.columns.str.strip()

        subject_faculty_map = {}
        for _, row in df_faculty.iterrows():
            subject = row['Subject']
            faculty_list = [f.strip() for f in str(row['Faculty']).split(',') if f.strip()]
            subject_faculty_map[subject] = faculty_list

    elif institution_type == "🏛️College":
        df_mapping = pd.read_excel(xls, sheet_name="SUBJECTS_COLLEGE")
        df_mapping['Teachers'] = df_mapping['Faculty']  # unify naming
        df_subject_hours_raw = pd.read_excel(xls, sheet_name="SUBJECT-ALLOCATION")
        df_subject_hours_raw.columns = ["Class", "Subject"]
        df_subject_hours = expand_class_subject_allocation(df_subject_hours_raw)
        df_classes = pd.DataFrame({'Class': df_subject_hours['Class'].unique()})

    else:
        raise ValueError("Invalid institution type")

    # Unified mapping logic
    subject_teacher_map = {}
    for _, row in df_mapping.iterrows():
        subject = row['Subject']
        teachers = [t.strip() for t in str(row['Teachers']).split(',') if t.strip()]
        subject_teacher_map[subject] = teachers

    return subject_teacher_map, df_subject_hours, df_classes 

    
# --- Generate actual period times including breaks inline ---
def generate_period_times(start_time_str, end_time_str, duration, breaks):
    start_time = datetime.strptime(start_time_str, "%H:%M")
    end_time = datetime.strptime(end_time_str, "%H:%M")
    period_times = []
    current = start_time
    while current + timedelta(minutes=duration) <= end_time:
        time_range = f"{current.strftime('%H:%M')} - {(current + timedelta(minutes=duration)).strftime('%H:%M')}"
        if current.strftime("%H:%M") in breaks:
            period_times.append(current.strftime("%H:%M"))
        period_times.append(time_range)
        current += timedelta(minutes=duration)
    for b_time in breaks:
        if b_time not in [p.split(" - ")[0] if " - " in p else p for p in period_times]:
            period_times.append(b_time)
    period_times = sorted(period_times, key=lambda x: datetime.strptime(x.split(' - ')[0] if ' - ' in x else x, "%H:%M"))
    return period_times

# --- Function to generate timetable ---
def generate_timetable(subject_teacher_map, subject_hours, days, periods, breaks, class_room):
    timetable = {day: {} for day in days}
    teacher_timetable = {}
    subject_alloc = {sub: 0 for sub in subject_hours}
    pr_subjects = [s for s in subject_hours if subject_hours[s]['PR'] >= 2]

    for day in days:
        i = 0
        while i < len(periods):
            period = periods[i]
            if period in breaks:
                for d in timetable:
                    timetable[d][period] = breaks[period]
                i += 1
                continue

            scheduled = False
            if i + 1 < len(periods) and periods[i + 1] not in breaks:
                for subject in pr_subjects:
                    if subject_alloc[subject] + 2 <= subject_hours[subject]['PR']:
                        teacher = random.choice(subject_teacher_map.get(subject, ["TBD"]))
                        for d in timetable:
                            timetable[d].setdefault(periods[i], "")
                            timetable[d].setdefault(periods[i + 1], "")
                        timetable[day][periods[i]] = f"{subject} (PR) ({teacher}) [{class_room}]"
                        timetable[day][periods[i + 1]] = f"{subject} (PR) ({teacher}) [{class_room}]"
                        subject_alloc[subject] += 2

                        if teacher not in teacher_timetable:
                            teacher_timetable[teacher] = {d: {} for d in days}
                        teacher_timetable[teacher][day][periods[i]] = f"{subject} (PR) [{class_room}]"
                        teacher_timetable[teacher][day][periods[i + 1]] = f"{subject} (PR) [{class_room}]"
                        scheduled = True
                        i += 2
                        break

            if scheduled:
                continue

            valid_subjects = [s for s in subject_hours if subject_alloc[s] < subject_hours[s]['TH'] + subject_hours[s]['PR']]
            if not valid_subjects:
                break

            subject = max(valid_subjects, key=lambda s: (subject_hours[s]['TH'] + subject_hours[s]['PR']) - subject_alloc[s])
            teacher = random.choice(subject_teacher_map.get(subject, ["TBD"]))
            subject_alloc[subject] += 1

            for d in timetable:
                timetable[d].setdefault(period, "")
            entry_text = f"{subject} TH ({teacher}) [{class_room}]"
            if subject_hours[subject]['PR'] > 0:
                entry_text = f"{subject} TH (PR) ({teacher}) [{class_room}]"
            timetable[day][period] = entry_text

            if teacher not in teacher_timetable:
                teacher_timetable[teacher] = {d: {} for d in days}
            teacher_timetable[teacher][day][period] = entry_text.replace(f"[{class_room}]", "").strip()
            i += 1

    timetable_df = pd.DataFrame(timetable).T
    timetable_df = timetable_df.fillna("")
    return timetable_df, teacher_timetable

# --- Load teacher-subject mapping ---
# Load from Excel
try:
    subject_teacher_map, df_subject_hours, df_classes = load_excel_data(excel_path, institution_type)
    

except Exception as e:
    st.error(f"Error loading Excel file: {e}")
    st.stop()
# Define stream_subject_map and subject_faculty_map from Excel if Coaching Institute is selected
stream_subject_map = {}
subject_faculty_map = {}

if institution_type == "🧪Coaching Institute":
    df_subjects_coaching = pd.read_excel(excel_path, sheet_name="SUBJECTS_COACHING")
    df_subjects_coaching.columns = df_subjects_coaching.columns.str.strip()
    df_subjects_coaching.rename(columns={'Stream': 'Class'}, inplace=True)
    stream_subject_map = df_subjects_coaching.groupby('Class')['Subject'].apply(list).to_dict()

    df_faculty = pd.read_excel(excel_path, sheet_name="FACULTY-SUBJECT")
    df_faculty.columns = df_faculty.columns.str.strip()
    subject_faculty_map = {
        row['Subject']: [f.strip() for f in str(row['Faculty']).split(',')]
        for _, row in df_faculty.iterrows()
    }
if institution_type == "🧪Coaching Institute":
    st.markdown("### 🏷️ Coaching Batch Setup")
    selected_class = st.selectbox("Select Stream (e.g., IIT-JEE-11):", df_classes['Class'].unique())
    selected_section = st.selectbox("Select Group:", ["A", "B"])
    class_room = st.text_input("Enter Classroom (e.g., CR-1)", "CR-1", key="coaching_room")
    st.subheader("Define Custom Schedule for Each Stream and Subject")
    st.markdown("#### ⏱️ Enter time, duration, and day for each subject:")
    custom_schedules = []
    subjects_for_stream = stream_subject_map.get(selected_class, [])

    for subject in subjects_for_stream:
        col1, col2, col3, col4 = st.columns([2, 2, 1, 2])
        with col1:
            day = st.selectbox(f"{subject} - Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"], key=f"{subject}_day")
        with col2:
            start_time = st.time_input(f"{subject} - Start Time", value=datetime.strptime("09:00", "%H:%M").time(), key=f"{subject}_start")
        with col3:
            duration = st.number_input(f"{subject} - Min", min_value=30, max_value=180, value=60, step=15, key=f"{subject}_duration")
        with col4:
            faculty = st.selectbox(f"{subject} - Faculty", subject_faculty_map.get(subject, ["TBD"]), key=f"{subject}_faculty")

        custom_schedules.append({
            "subject": subject,
            "day": day,
            "start_time": start_time,
            "duration": duration,
            "faculty": faculty
        })
    # ---------- DEFINE FLEXIBLE SESSIONS ----------
    st.markdown("### 🌀 Define Flexible Sessions")

    flexible_sessions = []
    num_flex_sessions = st.number_input("🎯How many flexible sessions do you want to define?", min_value=0, max_value=10, value=0, key="num_flex_sessions")

    for i in range(num_flex_sessions):
        st.markdown(f"#### Flexible Session {i+1}")
        col1, col2, col3 = st.columns(3)
        with col1:
            session_name = st.text_input(f"Session Name", key=f"flex_name_{i}")
        with col2:
            session_duration = st.number_input("Duration (periods)", min_value=1, max_value=5, value=1, key=f"flex_duration_{i}")
        with col3:
            preferred_day = st.selectbox("Preferred Day", ["Any", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"], key=f"flex_day_{i}")
    
        flexible_sessions.append({
            "name": session_name,
            "duration": session_duration,
            "day": preferred_day
        })

elif institution_type == "🏛️College":
    st.markdown("### 🏫 College Class Setup")
    selected_class = st.selectbox("Select Year (e.g., Sem 1-ETC):", df_classes['Class'].unique())
    selected_section = st.selectbox("Select Division:", ["A", "B", "C"])
    class_room = st.text_input("Enter Classroom (e.g., LH-1)", "LH-1", key="college_room")

else:
    # School
    selected_class = st.selectbox("Select Class:", df_classes['Class'].unique().tolist())
    selected_class = str(selected_class).replace("Std.", "").strip()
    selected_section = st.selectbox("Select Section:", ["A", "B", "C"])
    class_room = st.text_input("Enter Classroom (e.g., Room 101)", "Room 101", key="room_input")


# Select Class and Section (section from predefined list, not from Excel)
#available_classes = df_classes['Class'].unique().tolist()
#selected_class = st.selectbox("Select Class:", available_classes)
#selected_class = str(selected_class).replace("Std.", "").strip()


# Fixed section options
#sections = ["A", "B", "C"]
#selected_section = st.selectbox("Select Section:", sections)

# User input for classroom
#class_room = st.text_input("Enter Classroom (e.g., Room 101)", "Room 101", key="room_input")

# --- Configuration (unchanged) ---
days_options = {
    "Mon–Fri": ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
    "Mon–Sat": ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
}
st.markdown("### 🔔Configure Breaks")

break1_time = st.time_input("Short Break Time", value=datetime.strptime("10:00", "%H:%M").time(), key="short_break_time")
break1_duration = st.number_input("Short Break Duration (minutes)", min_value=5, max_value=30, value=15, key="short_break_duration")

break2_time = st.time_input("Lunch Break Time", value=datetime.strptime("12:00", "%H:%M").time(), key="lunch_break_time")
break2_duration = st.number_input("Lunch Break Duration (minutes)", min_value=10, max_value=60, value=30, key="lunch_break_duration")

breaks = {
    break1_time.strftime("%H:%M"): f"Short Break ({break1_duration} min)",
    break2_time.strftime("%H:%M"): f"Lunch Break ({break2_duration} min)"
}

selected_days_key = st.radio("📢Select Working Days:", list(days_options.keys()))
days = days_options[selected_days_key]

start_time = st.time_input("Select Start Time", value=datetime.strptime("07:45", "%H:%M").time())
end_time = st.time_input("Select End Time", value=datetime.strptime("14:30", "%H:%M").time())
period_duration = st.number_input("Enter Period Duration (in minutes)", min_value=30, max_value=120, value=60, step=5)

periods = generate_period_times(start_time.strftime("%H:%M"), end_time.strftime("%H:%M"), period_duration, breaks)
number_of_periods = len([p for p in periods if p not in breaks])
#st.info(f"Total periods per day (excluding breaks): {number_of_periods}")

# Weekly available hours
total_periods = number_of_periods * len(days)
total_minutes = total_periods * period_duration
available_hours = total_minutes // 60
st.metric(label="🗣️Available Teaching Hours", value=f"{available_hours} hrs", delta=None)

subjects = list(subject_teacher_map.keys())

# --- Step 2: Filter subjects by selected class ---
df_subject_hours['Class'] = df_subject_hours['Class'].astype(str).str.strip()
df_filtered_subjects = df_subject_hours[df_subject_hours['Class'] == selected_class]
subjects = df_filtered_subjects['Subject'].unique().tolist()

st.markdown("### 📖Define Weekly Hours per Subject")
subject_hours = {}
total_requested_hours = 0

# --- Step 3: Loop through each subject for TH/PR hours input ---
for subject in subjects:
    col1, col2 = st.columns(2)
    with col1:
        th = st.number_input(f"{subject} - Theory Hrs", min_value=0, max_value=45, value=3, key=f"{subject}_th")
    with col2:
        pr = st.number_input(f"{subject} - Practical Hrs", min_value=0, max_value=20, value=0, key=f"{subject}_pr")
    subject_hours[subject] = {"TH": th, "PR": pr}
    total_requested_hours += th + pr

# --- Step 4: Add two custom "TBD" subjects ---
st.markdown("### ⭐Add Optional Custom Subjects")

for i in range(1, 3):  # Two custom subjects
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        custom_subject = st.text_input(f"Custom Subject {i}", key=f"custom_sub_{i}")
    with col2:
        th = st.number_input(f"TH Hrs {i}", min_value=0, max_value=45, value=0, key=f"custom_th_{i}")
    with col3:
        pr = st.number_input(f"PR Hrs {i}", min_value=0, max_value=20, value=0, key=f"custom_pr_{i}")

    if custom_subject:
        subject_hours[custom_subject] = {"TH": th, "PR": pr}
        total_requested_hours += th + pr

st.success(f"🗣️Total subject hours requested: {total_requested_hours} hrs")
if total_requested_hours > available_hours:
    st.error("❌Total subject hours exceed available weekly hours! Please adjust.")

# Existing timetable versions in session state
if "generated_timetables" not in st.session_state:
    st.session_state.generated_timetables = {}

if "generate_clicked" not in st.session_state:
    st.session_state.generate_clicked = False


num_versions = st.selectbox("Number of Different Timetables to Generate:", [1, 2, 3])



# Trigger generation
if st.button("📝Generate Timetable"):
    st.session_state.generated_timetables.clear()
    st.session_state.generate_clicked = True
    for version in range(1, num_versions + 1):
        timetable_df, teacher_timetable = generate_timetable(
            subject_teacher_map, subject_hours, days, periods, breaks, class_room
        )

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            timetable_df.to_excel(writer, index=True, sheet_name='Class Timetable')
            for teacher, schedule in teacher_timetable.items():
                teacher_df = pd.DataFrame(schedule).T
                teacher_df.to_excel(writer, sheet_name=f"{teacher[:30]}")
        output.seek(0)

        st.session_state.generated_timetables[version] = {
            "df": timetable_df,
            "teacher": teacher_timetable,
            "excel": output.getvalue()
        }

# Display and download if generated
if st.session_state.generate_clicked and st.session_state.generated_timetables:
    for version, data in st.session_state.generated_timetables.items():
        st.markdown(f"## Version {version}: Timetable for {selected_class} {selected_section}")

        tt_title = f"{selected_class} {selected_section}"
        if institution_type == "🧪Coaching Institute":
            tt_title = f"Stream {selected_class} - Group {selected_section}"
        elif institution_type == "🏛️College":
            tt_title = f"{selected_class} - Division {selected_section}"

        #st.markdown(f"## Version {version}: Timetable for {tt_title}")


        def color_breaks(val):
            if isinstance(val, str) and 'Break' in val:
                return 'background-color: lightpink'
            return ''

        styled_df = data["df"].style.applymap(color_breaks)
        st.dataframe(styled_df, use_container_width=True)

        st.download_button(
            label=f"Download Class Timetable - Version {version}",
            data=data["excel"],
            file_name=f"{selected_class}_{selected_section}_Timetable_V{version}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_excel_{version}"
        )

        st.markdown("### 🧑‍🏫Faculty-wise Timetable")
        for teacher, schedule in data["teacher"].items():
            with st.expander(f"{teacher}"):
                teacher_df = pd.DataFrame(schedule).T
                styled_teacher_df = teacher_df.style.applymap(color_breaks)
                st.dataframe(styled_teacher_df, use_container_width=True)
