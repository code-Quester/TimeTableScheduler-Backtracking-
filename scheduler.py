import random

# Teacher class to store teacher details
class Teacher:
    def __init__(self, name, subjects, available_time_slots, max_hours):
        self.name = name
        self.subjects = subjects
        self.available_time_slots = available_time_slots
        self.max_hours = max_hours
        self.assigned_hours = 0
        self.assigned_time_slots = set()

# Course class to store course details
class Course:
    def __init__(self, name, batch, subject, course_type, required_hours=None, number_of_sessions=None, session_duration=None):
        self.name = name
        self.batch = batch
        self.subject = subject
        self.course_type = course_type
        if course_type == 'theory':
            self.required_hours = required_hours
            self.number_of_sessions = None
            self.session_duration = None
        elif course_type == 'lab':
            self.number_of_sessions = number_of_sessions
            self.session_duration = session_duration
            self.required_hours = None
        self.time_slots = []
        self.teacher = None
        self.classroom = None

# Batch class to manage courses and time slots for a batch
class Batch:
    def __init__(self, name):
        self.name = name
        self.courses = []
        self.used_time_slots = set()
        self.lab_days = {}

def get_day_from_slot(time_slot, periods_per_day):
    """Calculate the day index from a time slot index."""
    return time_slot // periods_per_day

def assign_lab_time_slots(course, session_index, time_slots, used_time_slots_by_course, periods_per_day, number_of_days):
    """Assign consecutive time slots for a lab session with at most one lab per day."""
    if session_index >= course.number_of_sessions:
        return True

    teacher = course.teacher
    duration = course.session_duration
    batch = course.batch

    days = list(range(number_of_days))
    random.shuffle(days)

    for day in days:
        if day in batch.lab_days and batch.lab_days[day] >= 1:
            continue

        start_slot = day * periods_per_day
        end_slot = start_slot + periods_per_day - duration + 1
        for slot in range(start_slot, end_slot):
            consecutive_slots = list(range(slot, slot + duration))
            if all(
                slot not in batch.used_time_slots and
                slot not in teacher.assigned_time_slots and
                slot in teacher.available_time_slots
                for slot in consecutive_slots
            ):
                for s in consecutive_slots:
                    course.time_slots.append(s)
                    batch.used_time_slots.add(s)
                    teacher.assigned_time_slots.add(s)
                    used_time_slots_by_course[s].add(course)
                teacher.assigned_hours += duration

                if day not in batch.lab_days:
                    batch.lab_days[day] = 0
                batch.lab_days[day] += 1

                if assign_lab_time_slots(course, session_index + 1, time_slots, used_time_slots_by_course, periods_per_day, number_of_days):
                    return True

                for s in consecutive_slots:
                    course.time_slots.remove(s)
                    batch.used_time_slots.remove(s)
                    teacher.assigned_time_slots.remove(s)
                    used_time_slots_by_course[s].remove(course)
                teacher.assigned_hours -= duration
                batch.lab_days[day] -= 1
                if batch.lab_days[day] == 0:
                    del batch.lab_days[day]

    return False

def assign_theory_time_slots(course, session_index, time_slots, used_time_slots_by_course, periods_per_day, number_of_days, max_theory_per_day):
    """Assign time slots for theory courses with constraints."""
    if session_index >= course.required_hours:
        return True

    teacher = course.teacher
    theory_hours_per_day = [0] * number_of_days
    for slot in course.time_slots:
        day = get_day_from_slot(slot, periods_per_day)
        theory_hours_per_day[day] += 1

    available_slots = [slot for slot in time_slots if slot not in course.batch.used_time_slots and slot not in teacher.assigned_time_slots and slot in teacher.available_time_slots]
    random.shuffle(available_slots)

    for time_slot in available_slots:
        day = get_day_from_slot(time_slot, periods_per_day)
        if theory_hours_per_day[day] >= max_theory_per_day:
            continue

        course.time_slots.append(time_slot)
        course.batch.used_time_slots.add(time_slot)
        teacher.assigned_time_slots.add(time_slot)
        used_time_slots_by_course[time_slot].add(course)
        teacher.assigned_hours += 1

        if assign_theory_time_slots(course, session_index + 1, time_slots, used_time_slots_by_course, periods_per_day, number_of_days, max_theory_per_day):
            return True

        course.time_slots.remove(time_slot)
        course.batch.used_time_slots.remove(time_slot)
        teacher.assigned_time_slots.remove(time_slot)
        used_time_slots_by_course[time_slot].remove(course)
        teacher.assigned_hours -= 1

    return False

def schedule(course_index, courses, teachers, time_slots, periods_per_day, number_of_days, max_theory_per_day=4):
    """Schedule all courses by assigning teachers and time slots with randomized teacher order."""
    if course_index >= len(courses):
        return True

    course = courses[course_index]
    randomized_teachers = random.sample(teachers, len(teachers))

    for teacher in randomized_teachers:
        if course.subject not in teacher.subjects:
            continue

        course.teacher = teacher
        used_time_slots_by_course = {ts: set() for ts in time_slots}

        if course.course_type == 'lab':
            if assign_lab_time_slots(course, 0, time_slots, used_time_slots_by_course, periods_per_day, number_of_days):
                if schedule(course_index + 1, courses, teachers, time_slots, periods_per_day, number_of_days, max_theory_per_day):
                    return True
                for ts in course.time_slots:
                    course.batch.used_time_slots.remove(ts)
                    teacher.assigned_time_slots.remove(ts)
                    used_time_slots_by_course[ts].remove(course)
                teacher.assigned_hours -= course.number_of_sessions * course.session_duration
                course.time_slots = []
                course.teacher = None
        elif course.course_type == 'theory':
            if assign_theory_time_slots(course, 0, time_slots, used_time_slots_by_course, periods_per_day, number_of_days, max_theory_per_day):
                if schedule(course_index + 1, courses, teachers, time_slots, periods_per_day, number_of_days, max_theory_per_day):
                    return True
                for ts in course.time_slots:
                    course.batch.used_time_slots.remove(ts)
                    teacher.assigned_time_slots.remove(ts)
                    used_time_slots_by_course[ts].remove(course)
                teacher.assigned_hours -= course.required_hours
                course.time_slots = []
                course.teacher = None

    return False

def assign_classrooms(courses, num_time_slots, num_classrooms):
    """Assign classrooms to courses for each time slot, ensuring labs use the same classroom for their block."""
    classroom_assignment = {}
    for time_slot in range(num_time_slots):
        courses_in_slot = [course for course in courses if time_slot in course.time_slots]
        if len(courses_in_slot) > num_classrooms:
            return None
        for i, course in enumerate(courses_in_slot):
            if course.course_type == 'lab' and course.time_slots[0] == time_slot:
                classroom = i
                for ts in course.time_slots:
                    classroom_assignment[(course.name, ts)] = classroom
            elif course.course_type == 'theory':
                classroom_assignment[(course.name, time_slot)] = i
    return classroom_assignment