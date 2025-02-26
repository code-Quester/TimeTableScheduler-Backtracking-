class Teacher:
    def __init__(self, name, subjects, available_time_slots, max_hours):
        self.name = name
        self.subjects = subjects
        self.available_time_slots = available_time_slots
        self.max_hours = max_hours
        self.assigned_hours = 0

class Course:
    def __init__(self, name, batch, subject, required_hours):
        self.name = name
        self.batch = batch
        self.subject = subject
        self.required_hours = required_hours
        self.time_slots = []
        self.teacher = None
        self.classroom = None

class Batch:
    def __init__(self, name):
        self.name = name
        self.courses = []
        self.used_time_slots = set()

def assign_time_slots(course, session_index, time_slots, used_time_slots_by_course):
    """Assign time slots to a course recursively."""
    if session_index >= course.required_hours:
        return True
    teacher = course.teacher
    for time_slot in time_slots:
        if time_slot not in teacher.available_time_slots or time_slot in course.batch.used_time_slots:
            continue
        if teacher.assigned_hours >= teacher.max_hours:
            continue
        course.time_slots.append(time_slot)
        course.batch.used_time_slots.add(time_slot)
        teacher.assigned_hours += 1
        used_time_slots_by_course[time_slot].add(course)
        if assign_time_slots(course, session_index + 1, time_slots, used_time_slots_by_course):
            return True
        course.time_slots.pop()
        course.batch.used_time_slots.remove(time_slot)
        teacher.assigned_hours -= 1
        used_time_slots_by_course[time_slot].remove(course)
    return False

def schedule(course_index, courses, teachers, time_slots):
    """Schedule all courses by assigning teachers and time slots."""
    if course_index >= len(courses):
        return True
    course = courses[course_index]
    for teacher in teachers:
        if course.subject not in teacher.subjects or teacher.assigned_hours + course.required_hours > teacher.max_hours:
            continue
        course.teacher = teacher
        used_time_slots_by_course = {ts: set() for ts in range(len(time_slots))}
        if assign_time_slots(course, 0, range(len(time_slots)), used_time_slots_by_course):
            if schedule(course_index + 1, courses, teachers, time_slots):
                return True
            for ts in course.time_slots:
                course.batch.used_time_slots.remove(ts)
            teacher.assigned_hours -= course.required_hours
            course.time_slots = []
            course.teacher = None
    return False

def assign_classrooms(courses, num_time_slots, num_classrooms):
    """Assign classrooms to courses for each time slot."""
    classroom_assignment = {}
    for time_slot in range(num_time_slots):
        courses_in_slot = [course for course in courses if time_slot in course.time_slots]
        if len(courses_in_slot) > num_classrooms:
            return None
        for i, course in enumerate(courses_in_slot):
            course.classroom = i
            classroom_assignment[(course.name, time_slot)] = i
    return classroom_assignment