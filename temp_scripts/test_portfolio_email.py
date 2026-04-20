"""
Test script for target portfolio email template generation.

This script tests:
1. HTML template generation
2. Email content formatting
3. Statistics display
"""

import sys

sys.path.insert(0, "/app")

from app.services.notification_service import get_notification_service


def test_email_template():
    """Test the target portfolio email template generation."""
    print("=" * 60)
    print("Target Portfolio Email Template Test")
    print("=" * 60)

    # Initialize service
    svc = get_notification_service()

    # Create mock portfolio data
    portfolio_data = {
        "target_portfolio": [
            {
                "rank": 1,
                "instrument": "SH600519",
                "benchmark_weight": 0.06,
                "score": 0.0312,
                "target_weight": 0.072,
                "deviation": 0.012,
                "deviation_pct": "+1.20%",
                "action": "超配",
            },
            {
                "rank": 2,
                "instrument": "SH300750",
                "benchmark_weight": 0.045,
                "score": 0.0089,
                "target_weight": 0.048,
                "deviation": 0.003,
                "deviation_pct": "+0.30%",
                "action": "超配",
            },
            {
                "rank": 3,
                "instrument": "SH601318",
                "benchmark_weight": 0.032,
                "score": -0.0156,
                "target_weight": 0.025,
                "deviation": -0.007,
                "deviation_pct": "-0.70%",
                "action": "低配",
            },
            {
                "rank": 4,
                "instrument": "SH600036",
                "benchmark_weight": 0.028,
                "score": 0.0001,
                "target_weight": 0.028,
                "deviation": 0.0,
                "deviation_pct": "+0.00%",
                "action": "持平",
            },
            {
                "rank": 5,
                "instrument": "SH000001",
                "benchmark_weight": 0.025,
                "score": -0.0234,
                "target_weight": 0.018,
                "deviation": -0.007,
                "deviation_pct": "-0.70%",
                "action": "低配",
            },
        ],
        "summary": {
            "benchmark": "csi300",
            "benchmark_name": "沪深300",
            "total_stocks": 300,
            "total_weight": 1.0,
            "overweight_count": 150,
            "underweight_count": 148,
            "neutral_count": 2,
            "max_deviation": 0.02,
            "generated_at": "2026-03-03T14:00:00",
            "target_date": "2026-03-03",
        },
    }

    # Generate HTML
    print("\nGenerating HTML template...")
    html_content = svc._build_target_portfolio_html(portfolio_data)

    # Validation
    print("\n" + "=" * 60)
    print("Validation")
    print("=" * 60)

    tests_passed = 0
    tests_total = 5

    # Test 1: HTML contains benchmark info
    if "沪深300" in html_content and "csi300" in html_content:
        print("✅ Test 1 PASSED: Benchmark info present")
        tests_passed += 1
    else:
        print("❌ Test 1 FAILED: Benchmark info missing")

    # Test 2: HTML contains portfolio table
    if "SH600519" in html_content and "SH300750" in html_content:
        print("✅ Test 2 PASSED: Portfolio items present")
        tests_passed += 1
    else:
        print("❌ Test 2 FAILED: Portfolio items missing")

    # Test 3: HTML contains statistics
    if "150" in html_content and "148" in html_content:
        print("✅ Test 3 PASSED: Statistics present")
        tests_passed += 1
    else:
        print("❌ Test 3 FAILED: Statistics missing")

    # Test 4: HTML contains action labels
    if "超配" in html_content and "低配" in html_content:
        print("✅ Test 4 PASSED: Action labels present")
        tests_passed += 1
    else:
        print("❌ Test 4 FAILED: Action labels missing")

    # Test 5: HTML is valid (basic check)
    if html_content.strip().startswith("<html") and "</html>" in html_content:
        print("✅ Test 5 PASSED: Valid HTML structure")
        tests_passed += 1
    else:
        print("❌ Test 5 FAILED: Invalid HTML structure")

    print(f"\n{'=' * 60}")
    print(f"Test Summary: {tests_passed}/{tests_total} tests passed")
    print(f"{'=' * 60}")

    # Save HTML for manual inspection
    output_file = "/app/temp_scripts/portfolio_email_preview.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"\nHTML preview saved to: {output_file}")
    print("You can open this file in a browser to inspect the email template.")

    return tests_passed == tests_total


if __name__ == "__main__":
    success = test_email_template()
    sys.exit(0 if success else 1)
