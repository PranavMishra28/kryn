#!/usr/bin/env python3
"""Grader for Community Task 01: Simple Bug Repair"""
import json
import sys
from pathlib import Path
from datetime import date

# Add the seed repo to path
sys.path.insert(0, str(Path(__file__).parent / 'seed_repo'))
from taskboard_lite.report import summarize

def test_date_range_bug():
    """Test that demonstrates the date range bug"""
    rows = [
        {'date': '2026-09-01', 'project': 'Project A', 'minutes': 60},
        {'date': '2026-09-02', 'project': 'Project A', 'minutes': 45},
        {'date': '2026-09-03', 'project': 'Project A', 'minutes': 120},
    ]
    
    # Test: should include 2026-09-01 but exclude 2026-09-03
    result = summarize(rows, start=date(2026, 9, 1), end=date(2026, 9, 3))
    
    # Current buggy behavior includes both start and end dates
    if result['count'] == 3:  # BUG: includes end date
        return False, "Date range bug detected: end date is included instead of excluded"
    
    # Correct behavior should exclude end date
    if result['count'] != 2:  # Should exclude 2026-09-03
        return False, f"Expected count=2, got {result['count']}"
    
    return True, "Date range boundary correctly implemented"

def test_existing_functionality():
    """Test that existing functionality still works"""
    rows = [
        {'date': '2026-09-01', 'project': 'Project A', 'minutes': 60},
        {'date': '2026-09-01', 'project': 'Project B', 'minutes': 30},
        {'date': '2026-09-02', 'project': 'Project A', 'minutes': 45},
    ]
    
    # Test no filters
    result = summarize(rows)
    if result['count'] != 3 or result['minutes'] != 135:
        return False, f"Basic summarize failed: count={result['count']}, minutes={result['minutes']}"
    
    # Test project filter
    result = summarize(rows, project='Project A')
    if result['count'] != 2 or result['minutes'] != 105:
        return False, f"Project filter failed: count={result['count']}, minutes={result['minutes']}"
    
    # Test empty range
    result = summarize(rows, start=date(2026, 9, 3), end=date(2026, 9, 4))
    if result['count'] != 0 or result['minutes'] != 0:
        return False, f"Empty range failed: count={result['count']}, minutes={result['minutes']}"
    
    return True, "Existing functionality preserved"

def main():
    """Run all tests"""
    results = []
    
    # Test the date range bug
    try:
        passed, message = test_date_range_bug()
        results.append({
            'test': 'date_range_bug',
            'passed': passed,
            'message': message
        })
    except Exception as e:
        results.append({
            'test': 'date_range_bug',
            'passed': False,
            'message': f'Exception: {str(e)}'
        })
    
    # Test existing functionality
    try:
        passed, message = test_existing_functionality()
        results.append({
            'test': 'existing_functionality',
            'passed': passed,
            'message': message
        })
    except Exception as e:
        results.append({
            'test': 'existing_functionality',
            'passed': False,
            'message': f'Exception: {str(e)}'
        })
    
    # Print results
    print(json.dumps(results, indent=2))
    
    # Exit with appropriate code
    if all(r['passed'] for r in results):
        return 0
    else:
        return 1

if __name__ == '__main__':
    sys.exit(main())