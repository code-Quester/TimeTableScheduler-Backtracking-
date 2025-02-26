from datetime import datetime, timedelta
import pandas as pd

def parse_time(time_str):
    """Parse a time string into a datetime object."""
    return datetime.strptime(time_str, "%H:%M")

def format_time(dt):
    """Format a datetime object into a time string."""
    return dt.strftime("%H:%M")

def generate_time_slots(num_days, num_periods, start_time, period_duration):
    """Generate time slot labels like 'Day1-9:30-10:30' with breaks."""
    breaks = [
        {"start": parse_time("11:30"), "end": parse_time("11:45")},  # Short break
        {"start": parse_time("13:45"), "end": parse_time("14:30")}   # Long break
    ]
    time_slots = []
    current_time = parse_time(start_time)
    periods_per_day = 0
    
    for day in range(num_days):
        day_periods = 0
        while day_periods < num_periods and periods_per_day < num_periods * num_days:
            in_break = False
            for b in breaks:
                if b["start"] <= current_time < b["end"]:
                    current_time = b["end"]
                    in_break = True
                    break
            if not in_break:
                end_time = current_time + timedelta(minutes=period_duration)
                for b in breaks:
                    if current_time < b["start"] and end_time > b["start"]:
                        end_time = b["start"]
                slot_label = f"Day{day+1}-{format_time(current_time)}-{format_time(end_time)}"
                time_slots.append(slot_label)
                current_time = end_time
                day_periods += 1
                periods_per_day += 1
        current_time = parse_time(start_time)  # Reset for next day
    return time_slots[:num_periods * num_days]  # Ensure exact number of periods

def create_batch_schedule_table(batch, courses, time_slots, num_days, num_periods):
    """Create a schedule table for a specific batch."""
    time_headers = sorted(set(ts.split('-', 1)[1] for ts in time_slots))
    table = {f"Day{day+1}": {header: [] for header in time_headers} for day in range(num_days)}
    
    for course in courses:
        if course.batch.name == batch:
            for ts in course.time_slots:
                day_str, time_range = time_slots[ts].split('-', 1)
                day = day_str
                info = f"{course.name} ({course.teacher.name}, Classroom {course.classroom})"
                table[day][time_range].append(info)
    
    # Convert to DataFrame-compatible format
    df_data = {}
    for day in table:
        df_data[day] = {header: ", ".join(table[day][header]) if table[day][header] else "No Class" for header in time_headers}
    return pd.DataFrame(df_data).T