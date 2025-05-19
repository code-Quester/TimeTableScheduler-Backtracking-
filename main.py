import streamlit as st
from scheduler import Teacher, Course, Batch, schedule, assign_classrooms
from utils import generate_time_slots, create_batch_schedule_table

st.title("Scheduling System")

# Time Slots Configuration
st.header("Time Slots Configuration")
num_days = st.number_input("Number of days", min_value=1, step=1, value=5)
num_periods = st.number_input("Periods per day", min_value=1, step=1, value=8)
start_time = st.text_input("Start time (HH:MM)", "09:30")
period_duration = st.number_input("Period duration (minutes)", min_value=15, step=15, value=60)
time_slot_labels, time_ranges = generate_time_slots(num_days, num_periods, start_time, period_duration)
total_time_slots = len(time_slot_labels)

# Teachers
st.header("Teachers")
num_teachers = st.number_input("Number of teachers", min_value=1, step=1, value=2)
teachers = []
all_time_slots = time_slot_labels

for i in range(num_teachers):
    with st.expander(f"Teacher {i+1}"):
        name = st.text_input(f"Name", key=f"t_name_{i}", value=f"Teacher{i+1}")
        subjects = st.text_input(f"Subjects (comma-separated)", key=f"t_subjects_{i}")
        unavailable = st.multiselect(f"Unavailable time slots", options=all_time_slots, key=f"t_unavailable_{i}")
        available_time_slots = [idx for idx, slot in enumerate(all_time_slots) if slot not in unavailable]
        max_hours = st.number_input(f"Max hours", min_value=1, step=1, key=f"t_hours_{i}", value=10)
        teachers.append({
            "name": name,
            "subjects": [s.strip() for s in subjects.split(",")] if subjects else [],
            "available_time_slots": available_time_slots,
            "max_hours": max_hours
        })

# Batches and Courses
st.header("Batches and Courses")
num_batches = st.number_input("Number of batches", min_value=1, step=1, value=2)
batches = []
for i in range(num_batches):
    with st.expander(f"Batch {i+1}"):
        batch_name = st.text_input(f"Batch name", key=f"b_name_{i}", value=f"Batch{i+1}")
        
        # Theory Courses
        num_theory_courses = st.number_input(f"Number of theory courses", min_value=0, key=f"b_theory_courses_{i}", value=2)
        theory_courses = []
        for j in range(num_theory_courses):
            name = st.text_input(f"Theory Course name (also the subject)", key=f"tc_name_{i}_{j}", value=f"Course{j+1}")
            required_hours = st.number_input(f"Required hours", min_value=1, key=f"tc_hours_{i}_{j}", value=2)
            theory_courses.append({"name": name, "subject": name, "required_hours": required_hours, "type": "theory"})
        
        # Practical Labs
        num_labs = st.number_input(f"Number of practical labs", min_value=0, key=f"b_labs_{i}", value=1)
        labs = []
        for j in range(num_labs):
            name = st.text_input(f"Lab name", key=f"l_name_{i}_{j}", value=f"Lab{j+1}")
            subject = st.text_input(f"Lab subject", key=f"l_subject_{i}_{j}", value=f"Lab{j+1}")
            number_of_sessions = st.number_input(f"Number of sessions", min_value=1, key=f"l_sessions_{i}_{j}", value=1)
            session_duration = st.selectbox(f"Session duration (hours)", options=[3, 4], key=f"l_duration_{i}_{j}")
            labs.append({
                "name": name,
                "subject": subject,
                "number_of_sessions": number_of_sessions,
                "session_duration": session_duration,
                "type": "lab"
            })
        
        batches.append({"name": batch_name, "theory_courses": theory_courses, "labs": labs})

# Classrooms
st.header("Classrooms")
num_classrooms = st.number_input("Number of classrooms", min_value=1, step=1, value=2)

# Schedule Button
if st.button("Generate Schedule"):
    with st.spinner("Scheduling..."):
        teacher_objects = [Teacher(t["name"], t["subjects"], t["available_time_slots"], t["max_hours"]) for t in teachers]
        batch_objects = []
        course_objects = []
        for b in batches:
            batch = Batch(b["name"])
            # Theory Courses
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
            # Practical Labs
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
                for batch in batch_objects:
                    schedule_table = create_batch_schedule_table(
                        batch.name, course_objects, time_slot_labels, num_days, num_periods, time_ranges
                    )
                    st.write(f"### Timetable for {batch.name}")
                    st.table(schedule_table)
                st.write("**Break Times:**")
                st.write("- Short Break: 11:30 - 11:45")
                st.write("- Long Break: 13:45 - 14:30")
            else:
                st.error("Failed: Not enough classrooms.")
        else:
            st.error("Failed: Unable to schedule with given constraints.")