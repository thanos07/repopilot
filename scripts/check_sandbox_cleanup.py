"""Opt-in live cleanup check. Place in RepoPilot's scripts/ directory.

Run: ~/repopilot-venv/bin/python scripts/check_sandbox_cleanup.py --live
Creates up to two billable E2B sandboxes; never calls the model or publishes.
Exit codes: 0 = both checks passed, 1 = failure/inconclusive, 2 = not opted in.
Only normal passing/failing pytest runs are covered, not process crashes.
"""
import argparse
from pathlib import Path
import sys
import os
import time


def run_case(label, source, expected, verifier, sandbox_api, not_found, api_key):
    print(f"\n--- {label} ---", flush=True)
    sandbox_ids = []
    matched = False
    removed = False
    try:
        result = verifier.verify(
            {"test_example.py": source}, on_created=sandbox_ids.append
        )
        matched = (result.status, result.exit_code) == expected
        print(f"Test result: {result.status}; exit code: {result.exit_code}")
        print(f"Result matches: {matched}")
    except Exception as error:
        # SDK exception messages can contain request details. Print class only.
        print(f"Verification error: {type(error).__name__}")
    finally:
        if sandbox_ids:
            sandbox_id = sandbox_ids[0]
            try:
                for attempt in range(3):
                    try:
                        sandbox_api.get_info(sandbox_id, api_key=api_key)
                    except not_found:
                        removed = True
                        break
                    if attempt < 2:
                        time.sleep(1)
                print("Cleanup: PASS; sandbox no longer exists." if removed else
                      "Cleanup: NOT CONFIRMED; sandbox still exists.")
            except Exception as error:
                print(f"Cleanup check inconclusive: {type(error).__name__}")
            finally:
                if not removed:
                    try:
                        sandbox_api.kill(sandbox_id, api_key=api_key)
                        print("Fallback cleanup requested; check remains failed.")
                    except Exception as error:
                        print(f"Fallback cleanup error: {type(error).__name__}")
                        print("Check the E2B dashboard; verifier expiry is the fallback.")
        else:
            print("Cleanup: NOT CHECKED; no sandbox ID recorded.")
    return matched and removed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow billable E2B checks")
    args = parser.parse_args()
    if not args.live:
        print("Not run. Add --live to create up to two E2B sandboxes.")
        return 2
    root = Path(__file__).resolve().parents[1]
    if not (root / "backend/manage.py").is_file():
        print("Place this file in the RepoPilot scripts/ directory.")
        return 1
    sys.path.insert(0, str(root / "backend"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        import django
        django.setup()
        from django.conf import settings
        from e2b import Sandbox
        from e2b.exceptions import NotFoundException
        from execution.sandbox import E2BVerifier
        if not settings.E2B_API_KEY or not settings.E2B_TEMPLATE:
            print("Set E2B_API_KEY and E2B_TEMPLATE in backend/.env.")
            return 1
        cases = [
            ("Passing test", "def test_example():\n    assert True\n", ("passed", 0)),
            ("Failing test", "def test_example():\n    assert False\n", ("failed", 1)),
        ]
        for label, source, expected in cases:
            if not run_case(label, source, expected, E2BVerifier(), Sandbox,
                            NotFoundException, settings.E2B_API_KEY):
                print("FAIL or INCONCLUSIVE. Stopping without creating another sandbox.")
                return 1
        print("\nPASS: both test outcomes matched and both sandboxes were removed.")
        return 0
    except Exception as error:
        print(f"Setup/check error: {type(error).__name__}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted. Check E2B for any remaining sandbox.")
        sys.exit(130)
