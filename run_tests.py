#!/usr/bin/env python3
"""Run backend tests."""
import subprocess
import sys

def run_backend_tests():
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/test_main.py", "-v"],
        cwd="/var/lib/alan-portfolio/workspaces/ryan/orbit-observatory-144-ryan-vo/backend",
        env={"PYTHONPATH": "."},
        capture_output=True,
        text=True
    )
    print("STDOUT:")
    print(result.stdout)
    print("STDERR:")
    print(result.stderr)
    print(f"Return code: {result.returncode}")
    return result.returncode == 0

if __name__ == "__main__":
    success = run_backend_tests()
    sys.exit(0 if success else 1)
