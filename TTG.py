import streamlit as st
import pandas as pd
import random
import os
from PIL import Image
from datetime import datetime, timedelta

# --- Streamlit UI Configuration ---
st.set_page_config(page_title="Timetable Generator", layout="wide")

# --- UI Inputs for Configurations ---
st.sidebar.header("Configuration")
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

# --- Top Header: Logo + Title ---
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if logo_path:
        st.image(logo_path, width=100)
    else:
        st.warning("Logo not found or not uploaded.")
with col_title:
    st.markdown(f"# {institute_name}")
    st.markdown("## Class Timetable Generator")

# --- Load teacher-subject mapping from Excel ---
@st.cache_data
def load_teacher_data(file_path):
    df = pd.read_excel(file_path, sheet_name="TeacherMapping")
    subject_teacher_map = {}
    for _, row in df.iterrows():
        subject = row['Subject']
        teachers = [t.strip() for t in row['Teachers'].split(',') if t.strip()]
        subject_teacher_map[subject] = teachers
    return subject_teacher_map

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
try:
    subject_teacher_map = load_teacher_data(excel_path)
except Exception as e:
    st.error(f"Error loading Excel file: {e}")
    st.stop()

# --- Configuration ---
classes = ["Class 5", "Class 6", "Class 7", "Class 8", "Class 9", "Class 10"]
sections = ["A", "B", "C"]
days_options = {
    "Mon–Fri": ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
    "Mon–Sat": ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
}
breaks = {
    '10:00': 'Short Break (15 min)',
    '12:00': 'Lunch Break (30 min)'
}

selected_class = st.selectbox("Select Class:", classes)
selected_section = st.selectbox("Select Section:", sections)
class_room = st.text_input("Enter Classroom (e.g., Room 101)", "Room 101")
selected_days_key = st.radio("Select Working Days:", list(days_options.keys()))
days = days_options[selected_days_key]

start_time = st.time_input("Select Start Time", value=datetime.strptime("07:45", "%H:%M").time())
end_time = st.time_input("Select End Time", value=datetime.strptime("14:30", "%H:%M").time())
period_duration = st.slider("Select Period Duration (minutes)", min_value=45, max_value=60, value=60)

periods = generate_period_times(start_time.strftime("%H:%M"), end_time.strftime("%H:%M"), period_duration, breaks)
number_of_periods = len([p for p in periods if p not in breaks])
st.info(f"Total periods per day (excluding breaks): {number_of_periods}")

# Weekly available hours
total_periods = number_of_periods * len(days)
total_minutes = total_periods * period_duration
available_hours = total_minutes // 60
st.success(f"Total available teaching hours per week: {available_hours} hrs")

subjects = list(subject_teacher_map.keys())
st.markdown("### Define Weekly Hours per Subject")
subject_hours = {}
total_requested_hours = 0
for subject in subjects:
    col1, col2 = st.columns(2)
    with col1:
        th = st.number_input(f"{subject} - Theory Hrs", min_value=0, max_value=45, value=3)
    with col2:
        pr = st.number_input(f"{subject} - Practical Hrs", min_value=0, max_value=20, value=0)
    subject_hours[subject] = {"TH": th, "PR": pr}
    total_requested_hours += th + pr

st.success(f"Total subject hours requested: {total_requested_hours} hrs")
if total_requested_hours > available_hours:
    st.error("Total subject hours exceed available weekly hours! Please adjust.")
num_versions = st.selectbox("Number of Different Timetables to Generate:", [1, 2, 3])

if st.button("Generate Timetable"):

    def color_breaks(val):
        if isinstance(val, str) and 'Break' in val:
            return 'background-color: lightpink'
        return ''

    for version in range(1, num_versions + 1):
        st.markdown(f"## Version {version}: Timetable for {selected_class} {selected_section}")

        timetable_df, teacher_timetable = generate_timetable(
            subject_teacher_map, subject_hours, days, periods, breaks, class_room
        )

        styled_df = timetable_df.style.applymap(color_breaks)
        st.dataframe(styled_df, use_container_width=True)

        st.download_button(
            label=f"Download Class Timetable - Version {version}",
            data=timetable_df.to_csv(),
            file_name=f"{selected_class}_{selected_section}_Timetable_V{version}.csv",
            mime="text/csv",
            key=f"download_class_v{version}"
        )

        st.markdown("### Faculty-wise Timetable")
        for teacher, schedule in teacher_timetable.items():
            with st.expander(f"{teacher}"):
                teacher_df = pd.DataFrame(schedule).T
                styled_teacher_df = teacher_df.style.applymap(color_breaks)
                st.dataframe(styled_teacher_df, use_container_width=True)
