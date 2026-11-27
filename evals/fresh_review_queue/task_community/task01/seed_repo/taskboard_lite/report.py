import csv
from datetime import datetime
from pathlib import Path

def summarize(rows, start=None, end=None, project=None):
    """Summarize time entries by date range and project."""
    count = 0
    minutes = 0
    
    for row in rows:
        # Parse date
        try:
            row_date = datetime.strptime(row['date'], '%Y-%m-%d').date()
        except (ValueError, KeyError):
            continue
            
        # Parse project
        row_project = row.get('project', '')
        
        # Check project filter
        if project and row_project != project:
            continue
            
        # Check date range - BUG: this uses inclusive ranges
        if start and row_date < start:
            continue
        if end and row_date > end:
            continue
            
        # Count and sum
        try:
            duration = int(row.get('minutes', 0))
        except (ValueError, TypeError):
            duration = 0
            
        count += 1
        minutes += duration
        
    return {'count': count, 'minutes': minutes}