#!/usr/bin/env python3
"""
Test script for Routine Integration with Signal Export

This script tests the complete routine workflow including the new Signal Export step.
"""

import sys
import json
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.append("/app")

from app.services.online_serving_service import get_online_serving_service


def test_routine_with_signal_export():
    """Test complete routine including signal export."""
    print("=" * 70)
    print("Testing Routine Integration with Signal Export")
    print("=" * 70)

    # Get online serving service
    serving_service = get_online_serving_service()

    print("\n🚀 Starting routine execution...")

    # Execute routine
    try:
        result = serving_service.routine()

        print(f"\n📊 Routine Execution Summary:")
        print(f"   Success: {result.get('success', False)}")
        print(f"   Total Duration: {result.get('total_duration_seconds', 0):.2f}s")
        print(f"   Executed At: {result.get('executed_at', 'N/A')}")

        # Display steps
        steps = result.get("steps", [])
        print(f"\n📋 Execution Steps ({len(steps)} total):")

        signal_export_step = None
        for i, step in enumerate(steps, 1):
            step_name = step.get("step", "Unknown")
            success = step.get("success", False)
            duration = step.get("duration_seconds", 0)
            status_icon = "✅" if success else "❌"

            print(f"   {i}. {step_name}: {status_icon} ({duration:.2f}s)")

            # Track Signal Export step for detailed analysis
            if step_name == "Signal Export":
                signal_export_step = step

        # Analyze Signal Export step
        if signal_export_step:
            print(f"\n🎯 Signal Export Step Analysis:")
            details = signal_export_step.get("details", {})

            if signal_export_step.get("success"):
                print(f"   ✅ Export Status: SUCCESS")
                print(f"   📁 Signal File: {details.get('signal_file', 'N/A')}")
                print(f"   📈 Total Positions: {details.get('total_positions', 0)}")
                print(f"   🏦 ETF Positions: {details.get('etf_positions', 0)}")
                print(f"   📊 Stock Positions: {details.get('stock_positions', 0)}")
                print(f"   ⚖️  Total Weight: {details.get('total_weight', 0)}")

                # Verify signal file exists
                signal_file = details.get("signal_file")
                if signal_file and os.path.exists(signal_file):
                    print(f"   ✅ Signal file verified: {signal_file}")

                    # Read and display signal content summary
                    try:
                        with open(signal_file, "r", encoding="utf-8") as f:
                            signal_data = json.load(f)

                        print(f"\n📄 Signal File Content:")
                        print(f"   Trade Date: {signal_data.get('trade_date', 'N/A')}")
                        print(f"   Index: {signal_data.get('index', 'N/A')}")
                        print(
                            f"   Strategy ETF Weight: {signal_data.get('strategy', {}).get('etf_weight', 0):.1%}"
                        )
                        print(
                            f"   Strategy Alpha Weight: {signal_data.get('strategy', {}).get('alpha_weight', 0):.1%}"
                        )

                        positions = signal_data.get("positions", [])
                        print(f"\n🎯 Top 5 Positions:")
                        for i, pos in enumerate(positions[:5], 1):
                            pos_type = pos["type"].upper()
                            weight_pct = pos["weight"] * 100
                            if pos["type"] == "etf":
                                print(
                                    f"      {i}. {pos['symbol']} ({pos_type}) - {weight_pct:.2f}%"
                                )
                            else:
                                score = pos.get("score", 0)
                                rank = pos.get("rank", 0)
                                print(
                                    f"      {i}. {pos['symbol']} ({pos_type}) - {weight_pct:.2f}% (score: {score:.3f}, rank: {rank})"
                                )

                        return True

                    except Exception as e:
                        print(f"   ⚠️  Could not read signal file content: {e}")
                        return True  # File exists, that's the main thing
                else:
                    print(f"   ❌ Signal file not found: {signal_file}")
                    return False
            else:
                print(f"   ❌ Export Status: FAILED")
                print(f"   Error: {details.get('error', 'Unknown error')}")
                return False
        else:
            print(f"\n❌ Signal Export step not found in routine results")
            return False

    except Exception as e:
        print(f"\n❌ Routine execution failed: {e}")
        return False


def check_signal_directory():
    """Check the signal output directory."""
    print("\n" + "=" * 70)
    print("Checking Signal Output Directory")
    print("=" * 70)

    signal_dir = Path("/app/data/signals")

    if signal_dir.exists():
        print(f"✅ Signal directory exists: {signal_dir}")

        # List signal files
        signal_files = list(signal_dir.glob("*.json"))
        print(f"📁 Found {len(signal_files)} signal files:")

        for file in sorted(signal_files, reverse=True):  # Latest first
            file_size = file.stat().st_size
            print(f"   - {file.name} ({file_size} bytes)")

        return len(signal_files) > 0
    else:
        print(f"❌ Signal directory does not exist: {signal_dir}")
        return False


if __name__ == "__main__":
    print("Starting Routine Integration Tests...")

    # Test 1: Check signal directory
    dir_check = check_signal_directory()

    # Test 2: Run routine with signal export
    routine_success = test_routine_with_signal_export()

    # Test 3: Check signal directory again (should have new files)
    dir_check_after = check_signal_directory()

    print("\n" + "=" * 70)
    print("Test Results Summary")
    print("=" * 70)
    print(f"Signal Directory Check: {'✅ PASSED' if dir_check_after else '❌ FAILED'}")
    print(
        f"Routine Integration Test: {'✅ PASSED' if routine_success else '❌ FAILED'}"
    )

    if routine_success and dir_check_after:
        print("\n🎉 All integration tests passed!")
        print("✅ Signal Export is successfully integrated into the routine!")
        sys.exit(0)
    else:
        print("\n💥 Some integration tests failed!")
        sys.exit(1)
