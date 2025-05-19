from datetime import datetime, timedelta
import pandas as pd

def parse_time(time_str):
    """Parse a time string into a datetime object."""
    return datetime.strptime(time_str.strip(), "%H:%M")

def format_time(dt):
    """Format a datetime object into a time string."""
    return dt.strftime("%H:%M")

def generate_time_slots(num_days, num_periods, start_time, period_duration):
    """Generate time slot labels like 'Day1-9:30-10:30' with breaks, limited to num_periods teaching slots."""
    breaks = [
        {"start": parse_time("11:30"), "end": parse_time("11:45")},  # Short break
        # {"start": parse_time("12:30"), "end": parse_time("13:30")},  # Extra break
        {"start": parse_time("13:45"), "end": parse_time("14:30")}    # Long break
    ]
    time_slots = []
    time_ranges = []  # Store (start_time, end_time) for each slot
    
    for day in range(num_days):
        current_time = parse_time(start_time)
        day_periods = 0
        while day_periods < num_periods:
            end_time = current_time + timedelta(minutes=period_duration)
            # Check if the slot overlaps with any break
            in_break = False
            for b in breaks:
                if current_time < b["end"] and end_time > b["start"]:
                    in_break = True
                    break
            if not in_break:
                slot_label = f"Day{day+1}-{format_time(current_time)}-{format_time(end_time)}"
                time_slots.append(slot_label)
                time_ranges.append((current_time, end_time))
                current_time = end_time
                day_periods += 1
            else:
                # Move to the end of the break
                for b in breaks:
                    if current_time < b["end"] and end_time > b["start"]:
                        current_time = b["end"]
                        break
    return time_slots, time_ranges

def create_batch_schedule_table(batch, courses, time_slots, num_days, num_periods, time_ranges,classroom_assignment):
    """Create a schedule table for a specific batch with breaks, starting at start_time and covering num_periods."""
    # Extract unique time headers from time_slots
    time_headers = sorted(set(ts.split('-', 1)[1] for ts in time_slots), key=lambda x: parse_time(x.split('-')[0]))

    # Initialize table with days and time headers
    table = {f"Day{day+1}": {header: [] for header in time_headers} for day in range(num_days)}
    
    # Add breaks to the table
    breaks = [
        {"start": "11:30", "end": "11:45", "label": "Short Break"},
        # {"start": "12:30", "end": "13:30", "label": "Extra Break"},
        {"start": "13:45", "end": "14:30", "label": "Long Break"}
    ]
    for day in range(num_days):
        # Get the time range for this day
        day_start_idx = day * num_periods
        day_end_idx = min((day + 1) * num_periods, len(time_ranges))
        day_time_range = time_ranges[day_start_idx:day_end_idx]
        if day_time_range:
            day_start_time = day_time_range[0][0]
            day_end_time = day_time_range[-1][1]
            for break_time in breaks:
                break_start = parse_time(break_time["start"])
                break_end = parse_time(break_time["end"])
                break_label = break_time["label"]
                # Only include breaks that fall within the day's time range
                if break_start >= day_start_time and break_end <= day_end_time:
                    for header in time_headers:
                        slot_start, slot_end = map(parse_time, header.split('-'))
                        if slot_start < break_end and slot_end > break_start:
                            table[f"Day{day+1}"][header].append(break_label)
    
    # Populate the table with course info
    for course in courses:
        if course.batch.name == batch:
            for ts in course.time_slots:
                if ts < len(time_slots):  # Ensure ts is valid
                    day_str, time_range = time_slots[ts].split('-', 1)
                    day = day_str
                    if time_range in time_headers:  # Only include if within headers
                        classroom = classroom_assignment.get((course.name, ts), "N/A")
                        info = f"{course.name} ({course.teacher.name}, Classroom {classroom})"
                        table[day][time_range].append(info)
    
    # Convert to DataFrame
    df_data = {}
    for day in table:
        df_data[day] = {header: ", ".join(table[day][header]) if table[day][header] else "No Class" for header in time_headers}
    return pd.DataFrame(df_data).T