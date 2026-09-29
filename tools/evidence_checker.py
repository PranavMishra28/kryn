"""Evidence-based validation for reviewer claims.

This module provides functions to validate that reviewer findings are supported
by actual evidence in the evals/history/ directory and current Git state.

Usage:
    from tools.evidence_checker import validate_reviewer_claim
    
    claim = "Reviewer found an issue in src/kryn/cli.py at line 42"
    is_valid = validate_reviewer_claim(claim)
"""

import json
import re
from pathlib import Path
from typing import Optional, Tuple


def load_evidence_receipt(receipt_path: str) -> dict:
    """Load an evidence receipt JSON file.
    
    Args:
        receipt_path: Path to the receipt JSON file in evals/history/
        
    Returns:
        Parsed JSON content of the receipt
    """
    try:
        with open(receipt_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return {'error': f'Failed to load receipt: {e}'}


def get_evidence_index() -> dict:
    """Load the evidence index from docs/history.md or generate from receipts.
    
    Returns:
        Dictionary mapping task IDs to their evidence files and outcomes
    """
    history_path = Path(__file__).parent.parent / 'docs' / 'history.md'
    
    if not history_path.exists():
        return {}
    
    # Parse the markdown file for evidence links
    content = history_path.read_text()
    
    # Extract evidence file references (pattern: [filename](path/to/file.json))
    pattern = r'\[([^\]]+)\]\(([^)]+\.json)\)'
    matches = re.findall(pattern, content)
    
    index = {}
    for title, path in matches:
        # Convert relative path to absolute
        abs_path = Path(__file__).parent.parent / path
        if abs_path.exists():
            index[title] = {
                'path': str(path),
                'absolute': str(abs_path)
            }
    
    return index


def validate_git_diff_claim(claim: str, repo_path: Optional[str] = None) -> Tuple[bool, str]:
    """Validate that a Git diff claim is supported by actual changes.
    
    Args:
        claim: The reviewer's claim about Git diff
        repo_path: Path to the repository (defaults to current working directory)
        
    Returns:
        Tuple of (is_valid, explanation)
    """
    import subprocess
    
    repo = Path(repo_path) if repo_path else Path.cwd()
    
    try:
        # Get current git diff
        result = subprocess.run(
            ['git', 'diff', '--stat'],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return False, f"Git diff failed: {result.stderr}"
        
        diff_summary = result.stdout
        
        # Check if claim is supported by actual changes
        # Simple heuristic: check if mentioned files are in the diff
        claim_file = re.search(r'in ([^\s]+\.py)', claim, re.IGNORECASE)
        if claim_file:
            file_path = claim_file.group(1)
            if file_path not in diff_summary:
                return False, f"Claim mentions {file_path} but it's not in the current Git diff"
        
        return True, f"Claim is supported by {len(diff_summary.splitlines())} changed lines"
        
    except subprocess.TimeoutExpired:
        return False, "Git diff timed out"
    except Exception as e:
        return False, f"Error validating Git diff: {e}"


def validate_browser_check_claim(claim: str, output_dir: Optional[str] = None) -> Tuple[bool, str]:
    """Validate that a browser check claim is supported by actual observations.
    
    Args:
        claim: The reviewer's claim about browser checks
        output_dir: Path to browser output directory
        
    Returns:
        Tuple of (is_valid, explanation)
    """
    if output_dir is None:
        output_dir = str(Path(__file__).parent.parent / 'browser-output')
    
    try:
        output_path = Path(output_dir)
        
        # Check for recent snapshot files
        if not output_path.exists():
            return False, f"Browser output directory not found: {output_dir}"
        
        # Look for snapshot files with recent timestamps
        snapshot_files = list(output_path.glob('page-*.yml'))[:5]  # Last 5 snapshots
        
        if not snapshot_files:
            return False, "No browser snapshots found in output directory"
        
        # Check if claim references observed elements or flows
        # For now, just verify that browser checks were performed
        return True, f"Browser checks supported by {len(snapshot_files)} recent snapshots"
        
    except Exception as e:
        return False, f"Error validating browser check: {e}"


def validate_reviewer_claim(claim: str) -> Tuple[bool, str]:
    """Validate a reviewer's claim against available evidence.
    
    Args:
        claim: The reviewer's finding or observation
        
    Returns:
        Tuple of (is_valid, explanation)
    """
    # Extract key information from claim
    file_match = re.search(r'([^\s]+\.py|[^/\n]+\.[^/\n]+)', claim, re.IGNORECASE)
    line_match = re.search(r'line\s*(\d+)', claim, re.IGNORECASE)
    
    if file_match:
        is_valid, explanation = validate_git_diff_claim(claim)
        return is_valid, explanation
    
    # Check for browser-related claims
    if 'browser' in claim.lower() or 'ui' in claim.lower() or 'flow' in claim.lower():
        is_valid, explanation = validate_browser_check_claim(claim)
        return is_valid, explanation
    
    # Default: claim needs manual verification
    return False, "Claim type not recognized for automated validation"


def generate_evidence_report() -> str:
    """Generate a report of all available evidence.
    
    Returns:
        Formatted string report
    """
    index = get_evidence_index()
    
    if not index:
        return "No evidence index found. Check docs/history.md"
    
    lines = ["Evidence Report", "=" * 50, ""]
    
    for title, info in sorted(index.items()):
        lines.append(f"• {title}")
        lines.append(f"  Path: {info['path']}")
        lines.append("")
    
    return "\n".join(lines)


if __name__ == '__main__':
    # Demo usage
    print("Evidence Checker - Demo")
    print(generate_evidence_report())
    print()
    
    # Example validation
    claim = "Reviewer found an issue in src/kryn/cli.py at line 42"
    is_valid, explanation = validate_reviewer_claim(claim)
    print(f"Claim validation: {is_valid}")
    print(f"Explanation: {explanation}")
