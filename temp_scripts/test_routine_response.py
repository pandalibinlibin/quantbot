"""
Test script to check routine API response structure.
"""

import sys

sys.path.insert(0, "/app")

import json
from app.services.online_serving_service import get_online_serving_service


def test_routine_response():
    """Check if routine returns target_portfolio."""
    print("=" * 60)
    print("Routine Response Structure Test")
    print("=" * 60)

    svc = get_online_serving_service()

    print("\nExecuting routine...")
    result = svc.routine()

    print(f"\nRoutine success: {result.get('success')}")
    print(f"Total duration: {result.get('total_duration_seconds')}s")

    # Check for target_portfolio
    target_portfolio = result.get("target_portfolio")
    portfolio_summary = result.get("portfolio_summary")

    print(f"\n--- Target Portfolio ---")
    print(f"target_portfolio exists: {target_portfolio is not None}")
    print(f"target_portfolio type: {type(target_portfolio)}")
    print(
        f"target_portfolio length: {len(target_portfolio) if target_portfolio else 0}"
    )

    print(f"\n--- Portfolio Summary ---")
    print(f"portfolio_summary exists: {portfolio_summary is not None}")
    if portfolio_summary:
        print(
            f"portfolio_summary: {json.dumps(portfolio_summary, indent=2, ensure_ascii=False)}"
        )

    # Show first 3 items if available
    if target_portfolio and len(target_portfolio) > 0:
        print(f"\n--- First 3 Portfolio Items ---")
        for item in target_portfolio[:3]:
            print(json.dumps(item, indent=2, ensure_ascii=False))

    # Check steps
    print(f"\n--- Steps ---")
    for step in result.get("steps", []):
        print(
            f"  {step.get('step')}: success={step.get('success')}, details={step.get('details')}"
        )

    # Print full result keys
    print(f"\n--- Result Keys ---")
    print(f"Keys: {list(result.keys())}")

    return target_portfolio is not None and len(target_portfolio) > 0


if __name__ == "__main__":
    success = test_routine_response()
    print(f"\n{'=' * 60}")
    print(
        f"Test {'PASSED' if success else 'FAILED'}: target_portfolio {'found' if success else 'NOT found'}"
    )
    print(f"{'=' * 60}")
    sys.exit(0 if success else 1)
