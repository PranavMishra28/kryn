#!/usr/bin/env python3
"""Verifier-driven repair controller for research rung 2.

This module implements the verifier-driven repair mechanism that processes
verification failures and generates targeted repair instructions.
"""
import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class VerifierDrivenRepairController:
    """Controller for verifier-driven repair mechanism."""
    
    def __init__(self, workspace: Path, evidence: Path):
        self.workspace = workspace
        self.evidence = evidence
        self.failure_patterns = {
            'retry-exhausted': {
                'expected': r'expected RuntimeError, fetch statuses \[429, 429\], and sleep calls \[60\]',
                'observed': r'observed RuntimeError, fetch statuses \[429, 429\], and sleep calls \[60, 120\]'
            }
        }
    
    def analyze_verification_results(self, result_file: Path) -> Dict:
        """Analyze verification results to identify specific failures."""
        with open(result_file, 'r') as f:
            results = json.load(f)
        
        failures = []
        for check_name, check_result in results.get('checks', {}).items():
            if not check_result.get('pass', False):
                failures.append({
                    'check': check_name,
                    'observed': check_result.get('observed', {}),
                    'output': check_result.get('output', '')
                })
        
        return {
            'pass': results.get('pass', False),
            'failures': failures,
            'total_checks': len(results.get('checks', {})),
            'passed_checks': sum(1 for c in results.get('checks', {}).values() if c.get('pass', False))
        }
    
    def extract_failure_traces(self, failure: Dict) -> Optional[Dict]:
        """Extract expected vs observed traces from failure information."""
        observed_output = failure.get('output', '')
        
        for pattern_name, pattern in self.failure_patterns.items():
            expected_match = re.search(pattern['expected'], observed_output)
            observed_match = re.search(pattern['observed'], observed_output)
            
            if expected_match and observed_match:
                return {
                    'pattern': pattern_name,
                    'expected': expected_match.group(0),
                    'observed': observed_match.group(0),
                    'check': failure.get('check')
                }
        
        return None
    
    def generate_repair_instructions(self, failure_traces: List[Dict]) -> str:
        """Generate repair instructions based on failure traces."""
        instructions = []
        
        for trace in failure_traces:
            if trace['pattern'] == 'retry-exhausted':
                instructions.append(
                    f"Repair the retry budget handling in {trace['check']}. "
                    f"Expected sleep calls: [60], observed: [60, 120]. "
                    f"Add a retry budget check before sleeping in both primary and secondary branches."
                )
        
        return "\n".join(instructions)
    
    def create_repair_prompt(self, original_prompt: str, repair_instructions: str) -> str:
        """Create a repair prompt by appending instructions to the original prompt."""
        return original_prompt + "\n\nREPAIR INSTRUCTIONS:\n" + repair_instructions
    
    def validate_repair(self, result_file: Path) -> Dict:
        """Validate that the repair passes all verification criteria."""
        analysis = self.analyze_verification_results(result_file)
        
        return {
            'repair_successful': analysis['pass'],
            'total_checks': analysis['total_checks'],
            'passed_checks': analysis['passed_checks'],
            'failures': analysis['failures']
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("original_prompt", type=Path)
    parser.add_argument("verification_result", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    
    workspace = args.workspace.resolve()
    evidence = args.evidence.resolve()
    original_prompt = args.original_prompt.resolve()
    verification_result = args.verification_result.resolve()
    output_dir = args.output_dir.resolve()
    
    if not (workspace / ".git").is_dir() or evidence.is_relative_to(workspace):
        parser.error("Use a Git fixture and private evidence outside the Agent workspace")
    
    output_dir.mkdir(parents=True, mode=0o700)
    
    # Initialize repair controller
    controller = VerifierDrivenRepairController(workspace, evidence)
    
    # Analyze verification results
    analysis = controller.analyze_verification_results(verification_result)
    
    # Extract failure traces
    failure_traces = []
    for failure in analysis['failures']:
        trace = controller.extract_failure_traces(failure)
        if trace:
            failure_traces.append(trace)
    
    if not failure_traces:
        print("No recognizable failure patterns found")
        return 1
    
    # Generate repair instructions
    repair_instructions = controller.generate_repair_instructions(failure_traces)
    
    # Create repair prompt
    repair_prompt = controller.create_repair_prompt(
        original_prompt.read_text().rstrip(),
        repair_instructions
    )
    
    # Save repair prompt
    repair_prompt_file = output_dir / "repair-prompt.txt"
    repair_prompt_file.write_text(repair_prompt)
    
    # Save analysis results
    output_data = {
        'original_pass': analysis['pass'],
        'total_checks': analysis['total_checks'],
        'passed_checks': analysis['passed_checks'],
        'failure_traces': failure_traces,
        'repair_instructions': repair_instructions,
        'repair_prompt': str(repair_prompt_file)
    }
    
    (output_dir / "analysis.json").write_text(
        json.dumps(output_data, indent=2) + "\n"
    )
    
    print(json.dumps({
        "result": str(output_dir / "analysis.json"),
        "repair_prompt": str(repair_prompt_file),
        "failure_count": len(failure_traces)
    }))
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
