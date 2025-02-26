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
time_slot_labels = generate_time_slots(num_days, num_periods, start_time, period_duration)
total_time_slots = len(time_slot_labels)
#st.write(f"Generated time slots: {', '.join(time_slot_labels)}")

# Teachers
st.header("Teachers")
num_teachers = st.number_input("Number of teachers", min_value=1, step=1, value=2)
teachers = []
all_time_slots = time_slot_labels  # Use generated time slots for selection

for i in range(num_teachers):
    with st.expander(f"Teacher {i+1}"):
        name = st.text_input(f"Name", key=f"t_name_{i}", value=f"Teacher{i+1}")
        subjects = st.text_input(f"Subjects (comma-separated)", key=f"t_subjects_{i}")
        
        # Select unavailable time slots
        unavailable = st.multiselect(f"Unavailable time slots", options=all_time_slots, key=f"t_unavailable_{i}")
        
        # Calculate available slots by excluding unavailable ones
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
        num_courses = st.number_input(f"Number of courses", min_value=1, key=f"b_courses_{i}", value=2)
        courses = []
        for j in range(num_courses):
            name = st.text_input(f"Course name (also the subject)", key=f"c_name_{i}_{j}", value=f"Course{j+1}")
            hours = st.number_input(f"Required hours", min_value=1, key=f"c_hours_{i}_{j}", value=2)
            courses.append({"name": name, "subject": name, "required_hours": hours})  # Set subject = name
        batches.append({"name": batch_name, "courses": courses})

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
            for c in b["courses"]:
                course = Course(c["name"], batch, c["subject"], c["required_hours"])
                batch.courses.append(course)
                course_objects.append(course)
            batch_objects.append(batch)

        if schedule(0, course_objects, teacher_objects, time_slot_labels):
            classroom_assignment = assign_classrooms(course_objects, total_time_slots, num_classrooms)
            if classroom_assignment:
                st.success("Schedule generated successfully!")
                for batch in batch_objects:
                    schedule_table = create_batch_schedule_table(batch.name, course_objects, time_slot_labels, num_days, num_periods)
                    st.write(f"### Timetable for {batch.name}")
                    st.table(schedule_table)
            else:
                st.error("Failed: Not enough classrooms.")
        else:
            st.error("Failed: Unable to schedule with given constraints.")