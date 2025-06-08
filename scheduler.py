import random
from collections import defaultdict
from typing import List, Set, Dict, Optional
import time

# Teacher class to store teacher details
class Teacher:
    def __init__(self, name, subjects, available_time_slots, max_hours):
        self.name = name
        self.subjects = subjects
        self.available_time_slots = set(available_time_slots)  # Convert to set for O(1) lookups
        self.max_hours = max_hours
        self.assigned_hours = 0
        self.assigned_time_slots = set()
        self.subject_courses = defaultdict(list)  # Cache for courses by subject

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
        self._cached_available_slots = None  # Cache for available slots

    def get_available_slots(self, teacher: Teacher, periods_per_day: int) -> List[int]:
        """Get cached available slots for this course with the given teacher."""
        if self._cached_available_slots is None:
            self._cached_available_slots = [
                slot for slot in teacher.available_time_slots
                if slot not in self.batch.used_time_slots
                and slot not in teacher.assigned_time_slots
            ]
        return self._cached_available_slots

# Batch class to manage courses and time slots for a batch
class Batch:
    def __init__(self, name):
        self.name = name
        self.courses = []
        self.used_time_slots = set()
        self.lab_days = {}
        self._theory_hours_per_day = defaultdict(int)  # Cache for theory hours per day

def get_day_from_slot(time_slot: int, periods_per_day: int) -> int:
    """Calculate the day index from a time slot index."""
    return time_slot // periods_per_day

def assign_lab_time_slots(
    course: Course,
    session_index: int,
    time_slots: List[int],
    used_time_slots_by_course: Dict[int, Set[Course]],
    periods_per_day: int,
    number_of_days: int,
    max_attempts: int = 1000
) -> bool:
    """Optimized lab time slot assignment with early termination."""
    if session_index >= course.number_of_sessions:
        return True

    teacher = course.teacher
    duration = course.session_duration
    batch = course.batch
    attempts = 0

    # Sort days by least number of labs for better distribution
    days = sorted(range(number_of_days), key=lambda d: batch.lab_days.get(d, 0))
    
    for day in days:
        if attempts >= max_attempts:
            return False
            
        if day in batch.lab_days and batch.lab_days[day] >= 1:
            continue

        start_slot = day * periods_per_day
        end_slot = start_slot + periods_per_day - duration + 1
        
        # Check if there's enough consecutive slots available
        available_slots = [
            slot for slot in range(start_slot, end_slot)
            if all(
                s in teacher.available_time_slots
                and s not in batch.used_time_slots
                and s not in teacher.assigned_time_slots
                for s in range(slot, slot + duration)
            )
        ]
        
        if not available_slots:
            continue

        # Try slots in random order
        random.shuffle(available_slots)
        for slot in available_slots:
            attempts += 1
            consecutive_slots = list(range(slot, slot + duration))
            
            # Assign slots
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

            # Backtrack
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

def assign_theory_time_slots(
    course: Course,
    session_index: int,
    time_slots: List[int],
    used_time_slots_by_course: Dict[int, Set[Course]],
    periods_per_day: int,
    number_of_days: int,
    max_theory_per_day: int,
    max_attempts: int = 1000
) -> bool:
    """Optimized theory time slot assignment with early termination."""
    if session_index >= course.required_hours:
        return True

    teacher = course.teacher
    attempts = 0
    
    # Get cached available slots
    available_slots = course.get_available_slots(teacher, periods_per_day)
    if not available_slots:
        return False

    # Sort slots by day with least theory hours
    available_slots.sort(key=lambda slot: course.batch._theory_hours_per_day[get_day_from_slot(slot, periods_per_day)])
    random.shuffle(available_slots)  # Add some randomness

    for time_slot in available_slots:
        attempts += 1
        if attempts >= max_attempts:
            return False

        day = get_day_from_slot(time_slot, periods_per_day)
        if course.batch._theory_hours_per_day[day] >= max_theory_per_day:
            continue

        # Assign slot
        course.time_slots.append(time_slot)
        course.batch.used_time_slots.add(time_slot)
        teacher.assigned_time_slots.add(time_slot)
        used_time_slots_by_course[time_slot].add(course)
        teacher.assigned_hours += 1
        course.batch._theory_hours_per_day[day] += 1

        if assign_theory_time_slots(course, session_index + 1, time_slots, used_time_slots_by_course, periods_per_day, number_of_days, max_theory_per_day):
            return True

        # Backtrack
        course.time_slots.remove(time_slot)
        course.batch.used_time_slots.remove(time_slot)
        teacher.assigned_time_slots.remove(time_slot)
        used_time_slots_by_course[time_slot].remove(course)
        teacher.assigned_hours -= 1
        course.batch._theory_hours_per_day[day] -= 1

    return False

def schedule(
    course_index: int,
    courses: List[Course],
    teachers: List[Teacher],
    time_slots: List[int],
    periods_per_day: int,
    number_of_days: int,
    max_theory_per_day: int = 4,
    max_attempts: int = 1000
) -> bool:
    """Optimized scheduling algorithm with early termination and better teacher assignment."""
    if course_index >= len(courses):
        return True

    course = courses[course_index]
    attempts = 0
    
    # Sort teachers by least assigned hours and most available slots
    eligible_teachers = [
        t for t in teachers
        if course.subject in t.subjects
        and t.assigned_hours < t.max_hours
    ]
    
    if not eligible_teachers:
        return False
        
    eligible_teachers.sort(key=lambda t: (t.assigned_hours, -len(t.available_time_slots)))
    random.shuffle(eligible_teachers)  # Add some randomness

    for teacher in eligible_teachers:
        attempts += 1
        if attempts >= max_attempts:
            return False

        course.teacher = teacher
        used_time_slots_by_course = {ts: set() for ts in time_slots}

        if course.course_type == 'lab':
            if assign_lab_time_slots(course, 0, time_slots, used_time_slots_by_course, periods_per_day, number_of_days):
                if schedule(course_index + 1, courses, teachers, time_slots, periods_per_day, number_of_days, max_theory_per_day):
                    return True
                # Backtrack
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
                # Backtrack
                for ts in course.time_slots:
                    course.batch.used_time_slots.remove(ts)
                    teacher.assigned_time_slots.remove(ts)
                    used_time_slots_by_course[ts].remove(course)
                teacher.assigned_hours -= course.required_hours
                course.time_slots = []
                course.teacher = None

    return False

def assign_classrooms(courses: List[Course], num_time_slots: int, num_classrooms: int) -> Optional[Dict]:
    """Optimized classroom assignment with early conflict detection."""
    classroom_assignment = {}
    classroom_usage = defaultdict(set)  # Track classroom usage by time slot
    
    # Sort courses by duration (labs first)
    sorted_courses = sorted(
        courses,
        key=lambda c: (c.course_type == 'lab', -len(c.time_slots) if c.time_slots else 0)
    )
    
    for course in sorted_courses:
        if course.course_type == 'lab':
            # Assign same classroom for all slots in a lab session
            available_classrooms = set(range(num_classrooms))
            for ts in course.time_slots:
                available_classrooms &= {c for c in range(num_classrooms) if ts not in classroom_usage[c]}
            
            if not available_classrooms:
                return None
                
            classroom = min(available_classrooms)  # Use lowest numbered available classroom
            for ts in course.time_slots:
                classroom_assignment[(course.name, ts)] = classroom
                classroom_usage[classroom].add(ts)
        else:
            # Assign classrooms for theory courses
            for ts in course.time_slots:
                available_classrooms = {c for c in range(num_classrooms) if ts not in classroom_usage[c]}
                if not available_classrooms:
                    return None
                classroom = min(available_classrooms)
                classroom_assignment[(course.name, ts)] = classroom
                classroom_usage[classroom].add(ts)
    
    return classroom_assignment