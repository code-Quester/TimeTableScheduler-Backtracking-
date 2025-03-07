import random  # Required for shuffling the teacher list

# Teacher class to store teacher details
class Teacher:
    def __init__(self, name, subjects, available_time_slots, max_hours):
        self.name = name
        self.subjects = subjects  # List of subjects the teacher can teach
        self.available_time_slots = available_time_slots  # List of time slot indices
        self.max_hours = max_hours  # Maximum hours the teacher can teach
        self.assigned_hours = 0  # Track hours assigned
        self.assigned_time_slots = set()  # Track assigned time slots

# Course class to store course details
class Course:
    def __init__(self, name, batch, subject, required_hours):
        self.name = name
        self.batch = batch  # The batch this course belongs to
        self.subject = subject  # Subject of the course
        self.required_hours = required_hours  # Number of hours needed
        self.time_slots = []  # Assigned time slots
        self.teacher = None  # Assigned teacher
        self.classroom = None  # Assigned classroom

# Batch class to manage courses and time slots for a batch
class Batch:
    def __init__(self, name):
        self.name = name
        self.courses = []  # List of courses in this batch
        self.used_time_slots = set()  # Track used time slots

def get_day_from_slot(time_slot, periods_per_day):
    """Calculate the day index from a time slot index."""
    return time_slot // periods_per_day

def assign_time_slots(course, session_index, time_slots, used_time_slots_by_course, periods_per_day, number_of_days):
    """
    Recursively assign time slots to a course with a max of 2 hours per day.
    
    Args:
        course: The course object being scheduled
        session_index: Current session being assigned (0 to required_hours-1)
        time_slots: List of available time slot indices
        used_time_slots_by_course: Dict tracking which courses use each time slot
        periods_per_day: Number of time slots per day
        number_of_days: Total number of days in the schedule
    Returns:
        True if time slots are successfully assigned, False otherwise
    """
    if session_index >= course.required_hours:
        return True
    
    teacher = course.teacher
    # Track hours assigned per day for this course
    hours_per_day = [0] * number_of_days
    for slot in course.time_slots:
        day = get_day_from_slot(slot, periods_per_day)
        hours_per_day[day] += 1
    
    # Determine strategy based on remaining hours and days
    remaining_hours = course.required_hours - session_index
    days_with_zero_or_one = sum(1 for h in hours_per_day if h < 2)
    
    for time_slot in time_slots:
        day = get_day_from_slot(time_slot, periods_per_day)
        
        # Skip if this assignment would exceed 2 hours on the day
        if hours_per_day[day] >= 2:
            continue
        
        # Existing constraints: teacher availability, batch conflicts, teacher conflicts, max hours
        if (time_slot not in teacher.available_time_slots or 
            time_slot in course.batch.used_time_slots or 
            time_slot in teacher.assigned_time_slots or 
            teacher.assigned_hours >= teacher.max_hours):
            continue
        
        # Apply distribution logic
        should_assign = True
        if course.required_hours <= number_of_days:
            # Case 1: Try to assign 1 hour per day if possible
            if hours_per_day[day] > 0 and any(h == 0 for h in hours_per_day):
                # Prefer days with 0 hours if available
                should_assign = False
        
        # If conditions are met, assign the slot
        if should_assign:
            course.time_slots.append(time_slot)
            course.batch.used_time_slots.add(time_slot)
            teacher.assigned_hours += 1
            teacher.assigned_time_slots.add(time_slot)
            used_time_slots_by_course[time_slot].add(course)
            
            if assign_time_slots(course, session_index + 1, time_slots, used_time_slots_by_course, periods_per_day, number_of_days):
                return True
            
            # Backtrack
            course.time_slots.pop()
            course.batch.used_time_slots.remove(time_slot)
            teacher.assigned_hours -= 1
            teacher.assigned_time_slots.remove(time_slot)
            used_time_slots_by_course[time_slot].remove(course)
    
    return False

def schedule(course_index, courses, teachers, time_slots, periods_per_day, number_of_days):
    """
    Schedule all courses by assigning teachers and time slots with randomized teacher order.
    
    Args:
        course_index: Index of the current course being scheduled
        courses: List of Course objects
        teachers: List of Teacher objects
        time_slots: List of available time slot indices
        periods_per_day: Number of time slots per day
        number_of_days: Total number of days in the schedule
    Returns:
        True if all courses are scheduled successfully, False otherwise
    """
    if course_index >= len(courses):
        return True  # All courses scheduled
    
    course = courses[course_index]
    randomized_teachers = random.sample(teachers, len(teachers))
    
    for teacher in randomized_teachers:
        if (course.subject not in teacher.subjects or 
            teacher.assigned_hours + course.required_hours > teacher.max_hours):
            continue
        
        course.teacher = teacher
        used_time_slots_by_course = {ts: set() for ts in range(len(time_slots))}
        
        if assign_time_slots(course, 0, time_slots, used_time_slots_by_course, periods_per_day, number_of_days):
            if schedule(course_index + 1, courses, teachers, time_slots, periods_per_day, number_of_days):
                return True
            # Backtrack
            for ts in course.time_slots:
                course.batch.used_time_slots.remove(ts)
                teacher.assigned_time_slots.remove(ts)
            teacher.assigned_hours -= course.required_hours
            course.time_slots = []
            course.teacher = None
    
    return False

def assign_classrooms(courses, num_time_slots, num_classrooms):
    """
    Assign classrooms to courses for each time slot.
    
    Args:
        courses: List of scheduled Course objects
        num_time_slots: Total number of time slots
        num_classrooms: Number of available classrooms
    Returns:
        Dict of (course_name, time_slot) -> classroom index, or None if impossible
    """
    classroom_assignment = {}
    for time_slot in range(num_time_slots):
        courses_in_slot = [course for course in courses if time_slot in course.time_slots]
        if len(courses_in_slot) > num_classrooms:
            return None  # Not enough classrooms
        for i, course in enumerate(courses_in_slot):
            course.classroom = i
            classroom_assignment[(course.name, time_slot)] = i
    return classroom_assignment

# Example usage
if __name__ == "__main__":
    # Define teachers
    teachers = [
        Teacher("Teacher1", ["Physics"], [0, 1, 2, 3, 4, 5, 6, 7], 6),  # 2 days, 4 slots/day
    ]
    
    # Define batches and courses
    batch1 = Batch("Batch1")
    courses = [
        Course("Physics", batch1, "Physics", 4),  # 4 hours of Physics
    ]
    batch1.courses = [courses[0]]
    
    # Define time slots (e.g., 0=Day1-9:30, 1=Day1-10:30, ..., 4=Day2-9:30, ...)
    time_slots = list(range(8))  # 2 days, 4 slots/day
    periods_per_day = 4
    number_of_days = 2
    
    # Run the scheduler
    if schedule(0, courses, teachers, time_slots, periods_per_day, number_of_days):
        print("Schedule found!")
        classroom_assignments = assign_classrooms(courses, len(time_slots), 1)
        if classroom_assignments:
            for course in courses:
                print(f"{course.name} (Batch {course.batch.name}):")
                print(f"  Teacher: {course.teacher.name}")
                print(f"  Time Slots: {course.time_slots}")
                for ts in course.time_slots:
                    day = ts // periods_per_day + 1
                    slot_in_day = ts % periods_per_day
                    print(f"    Slot {ts} (Day {day}, Period {slot_in_day + 1}): Classroom {classroom_assignments[(course.name, ts)]}")
        else:
            print("Failed to assign classrooms.")
    else:
        print("No valid schedule found.")