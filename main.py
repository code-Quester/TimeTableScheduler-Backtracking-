import streamlit as st
import sqlite3
import json
import bcrypt
from scheduler import Teacher, Course, Batch, schedule, assign_classrooms
from utils import generate_time_slots, create_batch_schedule_table
import pandas as pd
import io

# Database functions
def init_db():
    conn = sqlite3.connect("schedule_data.db")
    cursor = conn.cursor()

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT
        )
    """)

    # Check and update user_inputs table
    cursor.execute("PRAGMA table_info(user_inputs)")
    columns = {col[1]: col for col in cursor.fetchall()}
    if not columns:
        cursor.execute("""
            CREATE TABLE user_inputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                data TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
    elif 'user_id' not in columns:
        cursor.execute("""
            CREATE TABLE user_inputs_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                data TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        cursor.execute("INSERT INTO user_inputs_new (id, data) SELECT id, data FROM user_inputs")
        cursor.execute("DROP TABLE user_inputs")
        cursor.execute("ALTER TABLE user_inputs_new RENAME TO user_inputs")

    # Check and update schedules table
    cursor.execute("PRAGMA table_info(schedules)")
    columns = {col[1]: col for col in cursor.fetchall()}
    if not columns:
        cursor.execute("""
            CREATE TABLE schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                batch_name TEXT,
                data TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
    elif 'user_id' not in columns:
        cursor.execute("""
            CREATE TABLE schedules_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                batch_name TEXT,
                data TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        cursor.execute("INSERT INTO schedules_new (id, batch_name, data) SELECT id, batch_name, data FROM schedules")
        cursor.execute("DROP TABLE schedules")
        cursor.execute("ALTER TABLE schedules_new RENAME TO schedules")

    conn.commit()
    conn.close()

def register_user(username, password):
    try:
        conn = sqlite3.connect("schedule_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return False
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        st.error(f"Database error during registration: {e}")
        return False

def verify_user(username, password):
    try:
        conn = sqlite3.connect("schedule_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        if row:
            user_id, password_hash = row
            if bcrypt.checkpw(password.encode('utf-8'), password_hash):
                return user_id
        return None
    except sqlite3.Error as e:
        st.error(f"Database error during login: {e}")
        return None

def save_user_inputs(user_id, data_dict):
    try:
        conn = sqlite3.connect("schedule_data.db")
        cursor = conn.cursor()
        data_json = json.dumps(data_dict)
        cursor.execute("SELECT id FROM user_inputs WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE user_inputs SET data = ? WHERE user_id = ?", (data_json, user_id))
        else:
            cursor.execute("INSERT INTO user_inputs (user_id, data) VALUES (?, ?)", (user_id, data_json))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        st.error(f"Failed to save inputs: {e}")
        return False
    except json.JSONEncodeError as e:
        st.error(f"Failed to serialize input data: {e}")
        return False

def load_user_inputs(user_id):
    try:
        conn = sqlite3.connect("schedule_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM user_inputs WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
        return None
    except sqlite3.Error as e:
        st.error(f"Failed to load inputs: {e}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Failed to deserialize input data: {e}")
        return None

def save_schedule_to_db(user_id, batch_name, data_dict):
    try:
        conn = sqlite3.connect("schedule_data.db")
        cursor = conn.cursor()
        data_json = json.dumps(data_dict)
        cursor.execute("INSERT INTO schedules (user_id, batch_name, data) VALUES (?, ?, ?)", (user_id, batch_name, data_json))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        st.error(f"Failed to save schedule: {e}")
        return False

def load_schedules_from_db(user_id):
    try:
        conn = sqlite3.connect("schedule_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT batch_name, data FROM schedules WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [(name, json.loads(data)) for name, data in rows]
    except sqlite3.Error as e:
        st.error(f"Failed to load schedules: {e}")
        return []
    except json.JSONDecodeError as e:
        st.error(f"Failed to deserialize schedule data: {e}")
        return []

# Initialize database
init_db()

# Streamlit app
st.title("Timetable Scheduler")

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'login'

if st.session_state.page == 'login':
    st.subheader("Welcome")
    choice = st.selectbox("Choose an option", ["Login", "Register"])
    
    if choice == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user_id = verify_user(username, password)
            if user_id:
                st.session_state.user_id = user_id
                st.session_state.page = 'main'
                st.rerun()
            else:
                st.error("Invalid credentials")
    
    elif choice == "Register":
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        if st.button("Register"):
            if register_user(new_username, new_password):
                st.success("Registered successfully! Please log in.")
            else:
                st.error("Username already exists")

elif st.session_state.page == 'main':
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.error("Session expired. Please log in again.")
        st.session_state.page = 'login'
        st.rerun()

    # Load user's saved inputs first
    existing_data = load_user_inputs(user_id)
    if existing_data:
        # Update session state with all saved data before creating any widgets
        for key, value in existing_data.items():
            if key not in ['teachers', 'batches']:  # Handle these separately
                st.session_state[key] = value

    # Time Slots Configuration
    st.header("Time Slots Configuration")
    num_days = st.number_input("Number of days", min_value=1, step=1, value=st.session_state.get("num_days", 5), key="num_days")
    num_periods = st.number_input("Periods per day", min_value=1, step=1, value=st.session_state.get("num_periods", 7), key="num_periods")
    start_time = st.text_input("Start time (HH:MM)", value=st.session_state.get("start_time", "09:30"), key="start_time")
    period_duration = st.number_input("Period duration (minutes)", min_value=15, step=15, value=st.session_state.get("period_duration", 60), key="period_duration")
    time_slot_labels, time_ranges = generate_time_slots(num_days, num_periods, start_time, period_duration)
    total_time_slots = len(time_slot_labels)

    # Now handle the complex data structures after time slots are generated
    if existing_data:
        # Handle teachers data
        if 'teachers' in existing_data:
            for i, teacher in enumerate(existing_data['teachers']):
                st.session_state[f't_name_{i}'] = teacher['name']
                st.session_state[f't_subjects_{i}'] = ','.join(teacher['subjects'])
                st.session_state[f't_unavailable_{i}'] = [slot for idx, slot in enumerate(time_slot_labels) if idx not in teacher['available_time_slots']]
                st.session_state[f't_hours_{i}'] = teacher['max_hours']
        
        # Handle batches data
        if 'batches' in existing_data:
            for i, batch in enumerate(existing_data['batches']):
                st.session_state[f'b_name_{i}'] = batch['name']
                
                # Handle theory courses
                for j, course in enumerate(batch['theory_courses']):
                    st.session_state[f'tc_name_{i}_{j}'] = course['name']
                    st.session_state[f'tc_hours_{i}_{j}'] = course['required_hours']
                
                # Handle labs
                for j, lab in enumerate(batch['labs']):
                    st.session_state[f'l_name_{i}_{j}'] = lab['name']
                    st.session_state[f'l_sessions_{i}_{j}'] = lab['number_of_sessions']
                    st.session_state[f'l_duration_{i}_{j}'] = lab['session_duration']

    # Teachers
    st.header("Teachers")
    num_teachers = st.number_input("Number of teachers", min_value=1, step=1, value=st.session_state.get("num_teachers", 2), key="num_teachers")
    teachers = []
    all_time_slots = time_slot_labels

    for i in range(num_teachers):
        with st.expander(f"Teacher {i+1}"):
            name = st.text_input(f"Name", key=f"t_name_{i}", value=st.session_state.get(f"t_name_{i}", f"Teacher{i+1}"))
            subjects = st.text_input(f"Subjects (comma-separated)", key=f"t_subjects_{i}", value=st.session_state.get(f"t_subjects_{i}", ""))
            unavailable = st.multiselect(f"Unavailable time slots", options=all_time_slots, key=f"t_unavailable_{i}", default=st.session_state.get(f"t_unavailable_{i}", []))
            available_time_slots = [idx for idx, slot in enumerate(all_time_slots) if slot not in unavailable]
            max_hours = st.number_input(f"Max hours", min_value=1, step=1, key=f"t_hours_{i}", value=st.session_state.get(f"t_hours_{i}", 10))
            teachers.append({
                "name": name,
                "subjects": [s.strip() for s in subjects.split(",")] if subjects else [],
                "available_time_slots": available_time_slots,
                "max_hours": max_hours
            })

    # Batches and Courses
    st.header("Batches and Courses")
    num_batches = st.number_input("Number of batches", min_value=1, step=1, value=st.session_state.get("num_batches", 2), key="num_batches")
    batches = []
    for i in range(num_batches):
        with st.expander(f"Batch {i+1}"):
            batch_name = st.text_input(f"Batch name", key=f"b_name_{i}", value=st.session_state.get(f"b_name_{i}", f"Batch{i+1}"))
            num_theory_courses = st.number_input(f"Number of theory courses", min_value=0, key=f"b_theory_courses_{i}", value=st.session_state.get(f"b_theory_courses_{i}", 2))
            theory_courses = []
            for j in range(num_theory_courses):
                name = st.text_input(f"Theory Course name", key=f"tc_name_{i}_{j}", value=st.session_state.get(f"tc_name_{i}_{j}", f"Course{j+1}"))
                required_hours = st.number_input(f"Required hours", min_value=1, key=f"tc_hours_{i}_{j}", value=st.session_state.get(f"tc_hours_{i}_{j}", 2))
                theory_courses.append({"name": name, "subject": name, "required_hours": required_hours, "type": "theory"})
            num_labs = st.number_input(f"Number of practical labs", min_value=0, key=f"b_labs_{i}", value=st.session_state.get(f"b_labs_{i}", 1))
            labs = []
            for j in range(num_labs):
                name = st.text_input(f"Lab name", key=f"l_name_{i}_{j}", value=st.session_state.get(f"l_name_{i}_{j}", f"Lab{j+1}"))
                number_of_sessions = st.number_input(f"Number of sessions", min_value=1, key=f"l_sessions_{i}_{j}", value=st.session_state.get(f"l_sessions_{i}_{j}", 1))
                session_duration = st.selectbox(f"Session duration (hours)", options=[3, 4], key=f"l_duration_{i}_{j}", index=[3, 4].index(st.session_state.get(f"l_duration_{i}_{j}", 3)))
                labs.append({
                    "name": name,
                    "subject": name,
                    "number_of_sessions": number_of_sessions,
                    "session_duration": session_duration,
                    "type": "lab"
                })
            batches.append({"name": batch_name, "theory_courses": theory_courses, "labs": labs})

    # Classrooms
    st.header("Classrooms")
    num_classrooms = st.number_input("Number of classrooms", min_value=1, step=1, value=st.session_state.get("num_classrooms", 2), key="num_classrooms")

    # Save inputs
    if st.button("Save Inputs"):
        data_to_save = {
            "num_days": num_days,
            "num_periods": num_periods,
            "start_time": start_time,
            "period_duration": period_duration,
            "num_teachers": num_teachers,
            "teachers": teachers,
            "num_batches": num_batches,
            "batches": batches,
            "num_classrooms": num_classrooms
        }
        if save_user_inputs(user_id, data_to_save):
            st.success("Inputs saved successfully!")
        else:
            st.error("Failed to save inputs. Please try again.")

    # Clear inputs button with confirmation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clear Inputs"):
            st.session_state.show_clear_confirmation = True
    
    if st.session_state.get('show_clear_confirmation', False):
        st.warning("Are you sure you want to clear all your inputs? This action cannot be undone.")
        with col2:
            if st.button("Yes, Clear All Data"):
                # Clear all session state data
                for key in list(st.session_state.keys()):
                    if key not in ['user_id', 'page']:  # Preserve login state
                        del st.session_state[key]
                
                # Reset to default values
                st.session_state.update({
                    "num_days": 5,
                    "num_periods": 7,
                    "start_time": "09:30",
                    "period_duration": 60,
                    "num_teachers": 2,
                    "num_batches": 2,
                    "num_classrooms": 2
                })
                
                # Clear the database entry for this user
                try:
                    conn = sqlite3.connect("schedule_data.db")
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM user_inputs WHERE user_id = ?", (user_id,))
                    conn.commit()
                    conn.close()
                    st.success("All inputs have been cleared!")
                except sqlite3.Error as e:
                    st.error(f"Failed to clear data from database: {e}")
                
                st.session_state.show_clear_confirmation = False
                st.rerun()

    # Generate Schedule
    if st.button("Generate Schedule"):
        with st.spinner("Scheduling..."):
            teacher_objects = [Teacher(t["name"], t["subjects"], t["available_time_slots"], t["max_hours"]) for t in teachers]
            batch_objects = []
            course_objects = []
            for b in batches:
                batch = Batch(b["name"])
                for c in b["theory_courses"]:
                    course = Course(
                        name=c["name"],
                        batch=batch,
                        subject=c["subject"],
                        course_type=c["type"],
                        required_hours=c["required_hours"]
                    )
                    batch.courses.append(course)
                    course_objects.append(course)
                for l in b["labs"]:
                    course = Course(
                        name=l["name"],
                        batch=batch,
                        subject=l["subject"],
                        course_type=l["type"],
                        number_of_sessions=l["number_of_sessions"],
                        session_duration=l["session_duration"]
                    )
                    batch.courses.append(course)
                    course_objects.append(course)
                batch_objects.append(batch)

            time_slot_indices = list(range(total_time_slots))
            if schedule(0, course_objects, teacher_objects, time_slot_indices, num_periods, num_days):
                classroom_assignment = assign_classrooms(course_objects, total_time_slots, num_classrooms)
                if classroom_assignment:
                    st.success("Schedule generated successfully!")
                    batch_tables = {}
                    for batch in batch_objects:
                        schedule_table = create_batch_schedule_table(
                            batch.name, course_objects, time_slot_labels, num_days, num_periods, time_ranges, classroom_assignment
                        )
                        st.write(f"### Timetable for {batch.name}")
                        st.table(schedule_table)
                        batch_tables[batch.name] = schedule_table
                        save_schedule_to_db(user_id, batch.name, schedule_table.to_dict())

                    excel_file = io.BytesIO()
                    with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
                        for name, df in batch_tables.items():
                            df.to_excel(writer, sheet_name=name)
                    excel_file.seek(0)
                    st.download_button("📥 Download Timetables (Excel)", data=excel_file, file_name="timetables.xlsx")
                else:
                    st.error("Failed: Not enough classrooms.")
            else:
                st.error("Failed: Unable to schedule with given constraints.")

    # Display Previous Schedules
    st.header("Previously Saved Timetables")
    schedules = load_schedules_from_db(user_id)
    if schedules:
        for name, data_dict in schedules:
            df = pd.DataFrame.from_dict(data_dict)
            st.write(f"### {name}")
            st.table(df)
    else:
        st.write("No saved timetables found.")

    # Logout
    if st.button("Logout"):
        del st.session_state.user_id
        del st.session_state.page
        st.rerun()