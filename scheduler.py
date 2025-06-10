from collections import defaultdict
from typing import List, Set, Dict, Optional, Tuple
import logging

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Teacher class to store teacher details
class Teacher:
    def __init__(self, name, subjects, available_time_slots, max_hours):
        self.name = name
        self.subjects = set(subjects)  # Convert to set for O(1) lookups
        self.available_time_slots = set(available_time_slots)
        self.max_hours = max_hours
        self.assigned_hours = 0
        self.assigned_time_slots = set()
        self.subject_courses = defaultdict(list)
        # New: Track workload distribution
        self.daily_hours = defaultdict(int)
    
    def can_teach_more(self, additional_hours: int = 1) -> bool:
        """Check if teacher can take additional hours"""
        return self.assigned_hours + additional_hours <= self.max_hours
    
    def get_available_slots_for_day(self, day: int, periods_per_day: int) -> Set[int]:
        """Get available slots for a specific day"""
        day_start = day * periods_per_day
        day_end = day_start + periods_per_day
        return {slot for slot in self.available_time_slots 
                if day_start <= slot < day_end and slot not in self.assigned_time_slots}

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
        # New: Constraint tracking
        self._total_slots_needed = self._calculate_total_slots()
        self._difficulty_score = self._calculate_difficulty()
    
    def _calculate_total_slots(self) -> int:
        """Calculate total time slots needed for this course"""
        if self.course_type == 'lab':
            return self.number_of_sessions * self.session_duration
        return self.required_hours
    
    def _calculate_difficulty(self) -> int:
        """Calculate difficulty score for scheduling (higher = more difficult)"""
        # Labs are generally harder to schedule due to consecutive slot requirements
        base_difficulty = 2 if self.course_type == 'lab' else 1
        # More hours = more difficult
        slot_difficulty = self._total_slots_needed
        return base_difficulty * slot_difficulty
    
    def get_eligible_teachers(self, teachers: List[Teacher]) -> List[Teacher]:
        """Get teachers who can teach this course"""
        return [t for t in teachers 
                if self.subject in t.subjects and t.can_teach_more(self._total_slots_needed)]

# Batch class to manage courses and time slots for a batch
class Batch:
    def __init__(self, name):
        self.name = name
        self.courses = []
        self.used_time_slots = set()
        self.lab_days = defaultdict(int)  # Use defaultdict for cleaner code
        self.theory_hours_per_day = defaultdict(int)
        # New: Track lab scheduling details for constraint enforcement
        self.lab_start_slots = set()  # Track which slots start labs (for constraint checking)
    
    def can_add_theory_on_day(self, day: int, max_theory_per_day: int) -> bool:
        """Check if we can add more theory hours on a given day"""
        return self.theory_hours_per_day[day] < max_theory_per_day
    
    def can_add_lab_on_day(self, day: int, max_labs_per_day: int = 1) -> bool:
        """Check if we can add a lab on a given day"""
        return self.lab_days[day] < max_labs_per_day
    
    def add_lab_start_slot(self, start_slot: int):
        """Track that a lab starts at this slot"""
        self.lab_start_slots.add(start_slot)
    
    def remove_lab_start_slot(self, start_slot: int):
        """Remove tracking of lab start slot (for backtracking)"""
        self.lab_start_slots.discard(start_slot)

class ConstraintPropagator:
    """Implements constraint propagation for early pruning"""
    
    def __init__(self, courses: List[Course], teachers: List[Teacher], 
                 periods_per_day: int, number_of_days: int):
        self.courses = courses
        self.teachers = teachers
        self.periods_per_day = periods_per_day
        self.number_of_days = number_of_days
        self.total_slots = periods_per_day * number_of_days
    
    def propagate_constraints(self) -> bool:
        """
        Apply constraint propagation to eliminate impossible assignments
        Returns False if constraints cannot be satisfied
        """
        # Check basic feasibility
        for course in self.courses:
            eligible_teachers = course.get_eligible_teachers(self.teachers)
            if not eligible_teachers:
                logger.warning(f"No eligible teachers for course {course.name}")
                return False
            
            # Check if there are enough time slots available
            if not self._check_slot_availability(course):
                logger.warning(f"Not enough slots available for course {course.name}")
                return False
        
        return True
    
    def _check_slot_availability(self, course: Course) -> bool:
        """Check if there are potentially enough slots for a course with lab constraints"""
        eligible_teachers = course.get_eligible_teachers(self.teachers)
        max_available_slots = 0
        
        for teacher in eligible_teachers:
            if course.course_type == 'lab':
                # For labs, count available lab-eligible slots (slots 0 and 4 of each day)
                available_lab_slots = 0
                for day in range(self.number_of_days):
                    day_start = day * self.periods_per_day
                    lab_starts = [day_start, day_start + 4]  # Slots 0 and 4 of each day
                    
                    for start_slot in lab_starts:
                        # Check if we can fit the lab duration from this start slot
                        if start_slot + course.session_duration <= day_start + self.periods_per_day:
                            if all(slot in teacher.available_time_slots
                                   and slot not in course.batch.used_time_slots
                                   and slot not in teacher.assigned_time_slots
                                   for slot in range(start_slot, start_slot + course.session_duration)):
                                available_lab_slots += course.session_duration
                                break  # Only count one lab slot per day
                
                max_available_slots = max(max_available_slots, available_lab_slots)
            else:
                # For theory courses, count available slots excluding slot 3 on lab days
                available_slots = 0
                for slot in teacher.available_time_slots:
                    if (slot not in course.batch.used_time_slots 
                        and slot not in teacher.assigned_time_slots):
                        day = slot // self.periods_per_day
                        slot_in_day = slot % self.periods_per_day
                        
                        # Skip slot 3 if there's a lab on this day
                        # Since we're in constraint propagation phase, we can't check actual lab assignments
                        # So we'll be more lenient here and only do basic availability checks
                        available_slots += 1
                
                max_available_slots = max(max_available_slots, available_slots)
        
        return max_available_slots >= course._total_slots_needed
    
    def _has_lab_on_day(self, batch: Batch, day: int) -> bool:
        """
        Check if there's a lab scheduled on the given day.
        Uses the tracked lab start slots for accurate detection.
        """
        day_start = day * self.periods_per_day
        lab_start_slots = [day_start, day_start + 4]  # First and fifth slots of the day
        
        # Check if any lab start slots are tracked for this day
        for slot in lab_start_slots:
            if slot in batch.lab_start_slots:
                return True
        
        return False

class OptimizedScheduler:
    """Main scheduler class with optimized algorithms"""
    
    def __init__(self, periods_per_day: int, number_of_days: int, max_theory_per_day: int = 4):
        self.periods_per_day = periods_per_day
        self.number_of_days = number_of_days
        self.max_theory_per_day = max_theory_per_day
        self.total_slots = periods_per_day * number_of_days
        self.assignments_tried = 0
        self.max_assignments = 10000  # Prevent infinite loops
    
    def get_day_from_slot(self, time_slot: int) -> int:
        """Calculate the day index from a time slot index."""
        return time_slot // self.periods_per_day
    
    def get_course_priority(self, course: Course, teachers: List[Teacher]) -> Tuple[int, int, int]:
        """
        Calculate priority for course assignment (lower values = higher priority)
        Returns tuple for sorting: (available_teachers, difficulty, -total_slots)
        """
        eligible_teachers = course.get_eligible_teachers(teachers)
        available_teachers = len(eligible_teachers)
        
        # If no teachers available, this should be scheduled first (will fail fast)
        if available_teachers == 0:
            return (0, 0, 0)
        
        return (available_teachers, course._difficulty_score, -course._total_slots_needed)
    
    def get_teacher_priority(self, teacher: Teacher, course: Course) -> Tuple[int, int, int]:
        """
        Calculate priority for teacher assignment (lower values = higher priority)
        Returns tuple: (assigned_hours, negative_available_slots, workload_variance)
        """
        available_slots = len([
            slot for slot in teacher.available_time_slots
            if slot not in course.batch.used_time_slots
            and slot not in teacher.assigned_time_slots
        ])
        
        # Calculate workload variance (prefer balanced distribution)
        daily_hours_list = list(teacher.daily_hours.values())
        workload_variance = max(daily_hours_list) - min(daily_hours_list) if daily_hours_list else 0
        
        return (teacher.assigned_hours, -available_slots, workload_variance)
    
    def assign_lab_time_slots(self, course: Course, session_index: int) -> bool:
        """Optimized lab time slot assignment with strict constraints"""
        if session_index >= course.number_of_sessions:
            return True
        
        if self.assignments_tried >= self.max_assignments:
            return False
        
        teacher = course.teacher
        duration = course.session_duration
        batch = course.batch
        
        # Get days sorted by current lab load (prefer less loaded days)
        days = sorted(range(self.number_of_days), 
                     key=lambda d: (batch.lab_days[d], batch.theory_hours_per_day[d]))
        
        for day in days:
            if not batch.can_add_lab_on_day(day):
                continue
            
            # Find consecutive available slots for this day (only at positions 0 or 4)
            available_slots = self._find_consecutive_slots(teacher, batch, day, duration)
            
            if not available_slots:
                continue
            
            # Try the first available slot (deterministic choice)
            start_slot = available_slots[0]
            consecutive_slots = list(range(start_slot, start_slot + duration))
            
            # Validate lab constraint: must start at slot 0 or 4 of the day
            day_start = day * self.periods_per_day
            slot_position = start_slot - day_start
            if slot_position not in [0, 4]:
                logger.warning(f"Lab constraint violation: Lab for {course.name} cannot start at position {slot_position}")
                continue
            
            # Make assignment
            self._assign_slots(course, teacher, batch, consecutive_slots, day, is_lab=True)
            self.assignments_tried += 1
            
            logger.debug(f"Assigned lab {course.name} on day {day} starting at slot {start_slot} (position {slot_position})")
            
            # Recurse for next session
            if self.assign_lab_time_slots(course, session_index + 1):
                return True
            
            # Backtrack
            self._unassign_slots(course, teacher, batch, consecutive_slots, day, is_lab=True)
        
        return False
    
    def assign_theory_time_slots(self, course: Course, session_index: int) -> bool:
        """Optimized theory time slot assignment with lab-theory constraints"""
        if session_index >= course.required_hours:
            return True
        
        if self.assignments_tried >= self.max_assignments:
            return False
        
        teacher = course.teacher
        batch = course.batch
        
        # Get available slots sorted by preference (excludes slot 3 on lab days)
        available_slots = self._get_sorted_theory_slots(teacher, batch)
        
        for time_slot in available_slots:
            day = self.get_day_from_slot(time_slot)
            slot_in_day = time_slot % self.periods_per_day
            
            if not batch.can_add_theory_on_day(day, self.max_theory_per_day):
                continue
            
            # Additional constraint check: avoid slot 3 (4th slot) if lab is on the same day
            if slot_in_day == 3 and self._has_lab_on_day(batch, day):
                logger.debug(f"Skipping slot {time_slot} (position 3) for theory {course.name} due to lab on day {day}")
                continue
            
            # Make assignment
            self._assign_slots(course, teacher, batch, [time_slot], day, is_lab=False)
            self.assignments_tried += 1
            
            # Recurse for next hour
            if self.assign_theory_time_slots(course, session_index + 1):
                return True
            
            # Backtrack
            self._unassign_slots(course, teacher, batch, [time_slot], day, is_lab=False)
        
        return False
    
    def _find_consecutive_slots(self, teacher: Teacher, batch: Batch, day: int, duration: int) -> List[int]:
        """
        Find consecutive available slots for a given day with lab scheduling constraints.
        Labs can only start at slot 0 (first slot) or slot 4 (fifth slot) of each day.
        """
        day_start = day * self.periods_per_day
        
        # Lab constraint: Labs can only start at first slot (0) or fifth slot (4) of the day
        allowed_start_positions = [0, 4]  # Relative to day start
        available_slots = []
        
        for relative_start in allowed_start_positions:
            start_slot = day_start + relative_start
            
            # Check if we have enough slots for the lab duration
            if start_slot + duration > day_start + self.periods_per_day:
                continue  # Lab would extend beyond the day
            
            # Check if all required consecutive slots are available
            if all(slot in teacher.available_time_slots
                   and slot not in batch.used_time_slots
                   and slot not in teacher.assigned_time_slots
                   for slot in range(start_slot, start_slot + duration)):
                available_slots.append(start_slot)
        
        return available_slots
    
    def _get_sorted_theory_slots(self, teacher: Teacher, batch: Batch) -> List[int]:
        """
        Get theory slots sorted by preference (deterministic) with lab constraint enforcement.
        If a lab is scheduled starting at slot 0 or 4 on a day, avoid scheduling theory in slot 3.
        """
        available_slots = [
            slot for slot in teacher.available_time_slots
            if slot not in batch.used_time_slots
            and slot not in teacher.assigned_time_slots
        ]
        
        # Apply lab-theory constraint: filter out slot 3 (4th slot) if lab is on the same day
        filtered_slots = []
        for slot in available_slots:
            day = self.get_day_from_slot(slot)
            slot_in_day = slot % self.periods_per_day
            
            # Check if this is slot 3 (4th slot of the day) and if there's a lab on this day
            if slot_in_day == 3 and self._has_lab_on_day(batch, day):
                # Skip this slot due to lab constraint
                continue
            
            filtered_slots.append(slot)
        
        # Sort by: day load (prefer less loaded days), then by slot number
        filtered_slots.sort(key=lambda slot: (
            batch.theory_hours_per_day[self.get_day_from_slot(slot)],
            teacher.daily_hours[self.get_day_from_slot(slot)],
            slot
        ))
        
        return filtered_slots
    
    def _has_lab_on_day(self, batch: Batch, day: int) -> bool:
        """
        Check if there's a lab scheduled on the given day.
        Uses the tracked lab start slots for accurate detection.
        """
        day_start = day * self.periods_per_day
        lab_start_slots = [day_start, day_start + 4]  # First and fifth slots of the day
        
        # Check if any lab start slots are tracked for this day
        for slot in lab_start_slots:
            if slot in batch.lab_start_slots:
                return True
        
        return False
    
    def _assign_slots(self, course: Course, teacher: Teacher, batch: Batch, 
                     slots: List[int], day: int, is_lab: bool):
        """Helper method to assign time slots with constraint tracking"""
        for slot in slots:
            course.time_slots.append(slot)
            batch.used_time_slots.add(slot)
            teacher.assigned_time_slots.add(slot)
            teacher.assigned_hours += 1
            teacher.daily_hours[day] += 1
        
        if is_lab:
            batch.lab_days[day] += 1
            # Track lab start slot for constraint enforcement
            lab_start_slot = slots[0]  # First slot of the lab
            batch.add_lab_start_slot(lab_start_slot)
        else:
            batch.theory_hours_per_day[day] += len(slots)
    
    def _unassign_slots(self, course: Course, teacher: Teacher, batch: Batch,
                       slots: List[int], day: int, is_lab: bool):
        """Helper method to unassign time slots (backtrack) with constraint cleanup"""
        for slot in slots:
            course.time_slots.remove(slot)
            batch.used_time_slots.remove(slot)
            teacher.assigned_time_slots.remove(slot)
            teacher.assigned_hours -= 1
            teacher.daily_hours[day] -= 1
        
        if is_lab:
            batch.lab_days[day] -= 1
            if batch.lab_days[day] == 0:
                del batch.lab_days[day]
            # Remove lab start slot tracking
            lab_start_slot = slots[0]
            batch.remove_lab_start_slot(lab_start_slot)
        else:
            batch.theory_hours_per_day[day] -= len(slots)
            if batch.theory_hours_per_day[day] == 0:
                del batch.theory_hours_per_day[day]
    
    def schedule_courses(self, courses: List[Course], teachers: List[Teacher]) -> bool:
        """Main scheduling method"""
        # Apply constraint propagation first
        propagator = ConstraintPropagator(courses, teachers, self.periods_per_day, self.number_of_days)
        if not propagator.propagate_constraints():
            logger.error("Constraint propagation failed - problem is unsolvable")
            return False
        
        # Sort courses by priority (most constrained first)
        sorted_courses = sorted(courses, key=lambda c: self.get_course_priority(c, teachers))
        
        return self._schedule_recursive(0, sorted_courses, teachers)
    
    def _schedule_recursive(self, course_index: int, courses: List[Course], teachers: List[Teacher]) -> bool:
        """Recursive scheduling with optimized teacher selection"""
        if course_index >= len(courses):
            return True
        
        if self.assignments_tried >= self.max_assignments:
            logger.warning("Maximum assignments reached - terminating")
            return False
        
        course = courses[course_index]
        eligible_teachers = course.get_eligible_teachers(teachers)
        
        if not eligible_teachers:
            logger.warning(f"No eligible teachers for course {course.name}")
            return False
        
        # Sort teachers by priority (least loaded, most available slots first)
        eligible_teachers.sort(key=lambda t: self.get_teacher_priority(t, course))
        
        for teacher in eligible_teachers:
            course.teacher = teacher
            
            success = False
            if course.course_type == 'lab':
                success = self.assign_lab_time_slots(course, 0)
            elif course.course_type == 'theory':
                success = self.assign_theory_time_slots(course, 0)
            
            if success and self._schedule_recursive(course_index + 1, courses, teachers):
                return True
            
            # Backtrack - reset course state
            if course.time_slots:
                # Remove all assignments for this course
                for slot in course.time_slots[:]:
                    day = self.get_day_from_slot(slot)
                    batch = course.batch
                    teacher.assigned_time_slots.remove(slot)
                    teacher.assigned_hours -= 1
                    teacher.daily_hours[day] -= 1
                    batch.used_time_slots.remove(slot)
                    
                    if course.course_type == 'lab':
                        batch.lab_days[day] -= 1
                        if batch.lab_days[day] == 0:
                            del batch.lab_days[day]
                    else:
                        batch.theory_hours_per_day[day] -= 1
                        if batch.theory_hours_per_day[day] == 0:
                            del batch.theory_hours_per_day[day]
                
                course.time_slots = []
            
            course.teacher = None
        
        return False

# Backward compatibility functions (to work with existing main.py)
def get_day_from_slot(time_slot: int, periods_per_day: int) -> int:
    """Calculate the day index from a time slot index."""
    return time_slot // periods_per_day

def assign_lab_time_slots(course, session_index, time_slots, used_time_slots_by_course, 
                         periods_per_day, number_of_days, max_attempts=1000):
    """Backward compatibility wrapper"""
    scheduler = OptimizedScheduler(periods_per_day, number_of_days)
    return scheduler.assign_lab_time_slots(course, session_index)

def assign_theory_time_slots(course, session_index, time_slots, used_time_slots_by_course,
                            periods_per_day, number_of_days, max_theory_per_day, max_attempts=1000):
    """Backward compatibility wrapper"""
    scheduler = OptimizedScheduler(periods_per_day, number_of_days, max_theory_per_day)
    return scheduler.assign_theory_time_slots(course, session_index)

def schedule(course_index: int, courses: List[Course], teachers: List[Teacher],
            time_slots: List[int], periods_per_day: int, number_of_days: int,
            max_theory_per_day: int = 4, max_attempts: int = 1000) -> bool:
    """
    Main scheduling function - optimized version with backward compatibility
    """
    scheduler = OptimizedScheduler(periods_per_day, number_of_days, max_theory_per_day)
    scheduler.max_assignments = max_attempts
    
    # Only schedule remaining courses from course_index onward
    remaining_courses = courses[course_index:]
    
    if scheduler.schedule_courses(remaining_courses, teachers):
        logger.info(f"Successfully scheduled {len(remaining_courses)} courses")
        return True
    else:
        logger.error("Failed to schedule all courses")
        return False

def assign_classrooms(courses: List[Course], num_time_slots: int, num_classrooms: int) -> Optional[Dict]:
    """Optimized classroom assignment with better conflict resolution"""
    classroom_assignment = {}
    classroom_usage = defaultdict(set)
    
    # Sort courses by complexity and duration
    sorted_courses = sorted(courses, key=lambda c: (
        c.course_type == 'lab',  # Labs first (harder to place)
        -len(c.time_slots) if c.time_slots else 0,  # Longer courses first
        c.name  # Deterministic tie-breaker
    ))
    
    for course in sorted_courses:
        if not course.time_slots:
            continue
            
        if course.course_type == 'lab':
            # Labs need same classroom for all sessions
            available_classrooms = set(range(num_classrooms))
            for ts in course.time_slots:
                available_classrooms &= {
                    c for c in range(num_classrooms) 
                    if ts not in classroom_usage[c]
                }
            
            if not available_classrooms:
                logger.error(f"No classroom available for lab course {course.name}")
                return None
            
            # Use the classroom with least current usage for better distribution
            classroom = min(available_classrooms, key=lambda c: len(classroom_usage[c]))
            course.classroom = classroom
            
            for ts in course.time_slots:
                classroom_assignment[(course.name, ts)] = classroom
                classroom_usage[classroom].add(ts)
        else:
            # Theory courses can use different classrooms for different slots
            for ts in course.time_slots:
                available_classrooms = {
                    c for c in range(num_classrooms) 
                    if ts not in classroom_usage[c]
                }
                
                if not available_classrooms:
                    logger.error(f"No classroom available for theory course {course.name} at slot {ts}")
                    return None
                
                # Use least utilized classroom
                classroom = min(available_classrooms, key=lambda c: len(classroom_usage[c]))
                classroom_assignment[(course.name, ts)] = classroom
                classroom_usage[classroom].add(ts)
    
    logger.info(f"Successfully assigned classrooms to {len(courses)} courses")
    return classroom_assignment