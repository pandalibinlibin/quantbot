"""
Test script for data source configuration.

This script tests:
1. Tushare API connection and token configuration
2. Index components fetching from Tushare
3. Trading calendar retrieval
4. Configuration files

Run with: docker compose exec backend python /app/temp_scripts/test_data_source.py
"""

import sys
import os

# Add app to path
sys.path.insert(0, "/app")


def test_tushare_connection():
    """Test Tushare API connection."""
    print("\n" + "=" * 60)
    print("Test 1: Tushare API Connection")
    print("=" * 60)

    try:
        import tushare as ts
        from app.core.config import settings

        token = settings.TUSHARE_TOKEN
        if not token:
            print("❌ TUSHARE_TOKEN not configured")
            return False

        print(f"✅ TUSHARE_TOKEN configured: {token[:10]}...{token[-10:]}")

        # Set token and create API instance
        ts.set_token(token)
        pro = ts.pro_api()

        # Test API with a simple query - use daily API which has lower permission requirement
        df = pro.daily(ts_code="000001.SZ", start_date="20260101", end_date="20260110")

        if df is not None and not df.empty:
            print(f"✅ Tushare API connection successful")
            print(f"   Retrieved {len(df)} daily records for 000001.SZ")
            return True
        else:
            # Try trade_cal as fallback
            df = pro.trade_cal(
                exchange="SSE", start_date="20260101", end_date="20260131"
            )
            if df is not None and not df.empty:
                print(f"✅ Tushare API connection successful (via trade_cal)")
                print(f"   Retrieved {len(df)} calendar entries")
                return True
            print("❌ Tushare API returned empty result")
            return False

    except Exception as e:
        error_msg = str(e)
        if "权限" in error_msg or "permission" in error_msg.lower():
            print(f"⚠️ Tushare API permission issue: {e}")
            print(
                "   Note: Some APIs require higher Tushare points. Visit https://tushare.pro/document/1?doc_id=108"
            )
            return "permission"
        print(f"❌ Tushare connection failed: {e}")
        return False


def test_index_components():
    """Test index components fetching via Tushare (2120 points - should work now)."""
    print("\n" + "=" * 60)
    print("Test 2: Index Components (CSI300)")
    print("=" * 60)

    try:
        import tushare as ts
        from app.core.config import settings

        token = settings.TUSHARE_TOKEN
        ts.set_token(token)
        pro = ts.pro_api()

        # Test both index_member and index_weight (both should work with 2120 points)
        print("Testing index_member API...")
        df_member = pro.index_member(index_code="000300.SH")

        print("Testing index_weight API...")
        df_weight = pro.index_weight(index_code="000300.SH")

        success = False

        if df_member is not None and not df_member.empty:
            components = df_member["con_code"].unique().tolist()
            print(f"✅ index_member: Retrieved {len(components)} CSI300 components")
            print(f"   Sample: {components[:5]}")
            success = True
        else:
            print("⚠️ index_member returned no data")

        if df_weight is not None and not df_weight.empty:
            weights = df_weight["con_code"].unique().tolist()
            print(
                f"✅ index_weight: Retrieved {len(weights)} CSI300 components with weights"
            )
            print(f"   Sample: {weights[:5]}")
            success = True
        else:
            print("⚠️ index_weight returned no data")

        return success

    except Exception as e:
        error_msg = str(e)
        if "权限" in error_msg or "permission" in error_msg.lower():
            print(f"⚠️ Index components API permission issue: {e}")
            print("   Note: This should work with 2120+ points")
            return "permission"
        print(f"❌ Index components test failed: {e}")
        return False


def test_trading_calendar():
    """Test trading calendar retrieval via Tushare (2120 points - should work now)."""
    print("\n" + "=" * 60)
    print("Test 3: Trading Calendar")
    print("=" * 60)

    try:
        import tushare as ts
        from app.core.config import settings

        token = settings.TUSHARE_TOKEN
        ts.set_token(token)
        pro = ts.pro_api()

        # Get trading calendar
        df = pro.trade_cal(exchange="SSE", start_date="20260101", end_date="20260331")

        if df is not None and not df.empty:
            trading_days = df[df["is_open"] == 1]
            print(f"✅ Retrieved {len(trading_days)} trading days (Q1 2026)")
            print(f"   Total calendar days: {len(df)}")
            print(
                f"   Sample trading days: {trading_days['cal_date'].head(5).tolist()}"
            )
            return True
        else:
            print("❌ No trading calendar returned")
            return False

    except Exception as e:
        error_msg = str(e)
        if "权限" in error_msg or "permission" in error_msg.lower():
            print(f"⚠️ Trading calendar API permission issue: {e}")
            print("   Note: This should work with 2120+ points")
            return "permission"
        print(f"❌ Trading calendar test failed: {e}")
        return False


def test_single_stock_data():
    """Test fetching data for a single stock via Tushare."""
    print("\n" + "=" * 60)
    print("Test 4: Single Stock Data (000001.SZ - 平安银行)")
    print("=" * 60)

    try:
        import tushare as ts
        from app.core.config import settings

        token = settings.TUSHARE_TOKEN
        ts.set_token(token)
        pro = ts.pro_api()

        # Fetch daily data for Ping An Bank
        df = pro.daily(ts_code="000001.SZ", start_date="20260101", end_date="20260131")

        if df is not None and not df.empty:
            print(f"✅ Retrieved {len(df)} records for 000001.SZ")
            print(f"   Columns: {df.columns.tolist()}")
            print(
                f"   Date range: {df['trade_date'].min()} to {df['trade_date'].max()}"
            )
            return True
        else:
            print("❌ No data returned for 000001.SZ")
            return False

    except Exception as e:
        error_msg = str(e)
        if "权限" in error_msg or "permission" in error_msg.lower():
            print(f"⚠️ Daily data API permission issue: {e}")
            return "permission"
        print(f"❌ Single stock data test failed: {e}")
        return False


def test_financial_data():
    """Test financial data APIs (available with 2120+ points)."""
    print("\n" + "=" * 60)
    print("Test 5: Financial Data (000001.SZ - 平安银行)")
    print("=" * 60)

    try:
        import tushare as ts
        from app.core.config import settings

        token = settings.TUSHARE_TOKEN
        ts.set_token(token)
        pro = ts.pro_api()

        success = False

        # Test income statement (利润表)
        print("Testing income statement...")
        df_income = pro.income(ts_code="000001.SZ", period="20251231")
        if df_income is not None and not df_income.empty:
            print(f"✅ Income statement: {len(df_income)} records")
            success = True
        else:
            print("⚠️ No income statement data")

        # Test balance sheet (资产负债表)
        print("Testing balance sheet...")
        df_balance = pro.balancesheet(ts_code="000001.SZ", period="20251231")
        if df_balance is not None and not df_balance.empty:
            print(f"✅ Balance sheet: {len(df_balance)} records")
            success = True
        else:
            print("⚠️ No balance sheet data")

        # Test daily basic info (每日指标)
        print("Testing daily basic metrics...")
        df_basic = pro.daily_basic(ts_code="000001.SZ", trade_date="20260115")
        if df_basic is not None and not df_basic.empty:
            print(f"✅ Daily basic metrics: {len(df_basic)} records")
            print(f"   PE: {df_basic['pe'].iloc[0] if not df_basic.empty else 'N/A'}")
            success = True
        else:
            print("⚠️ No daily basic data")

        return success

    except Exception as e:
        error_msg = str(e)
        if "权限" in error_msg or "permission" in error_msg.lower():
            print(f"⚠️ Financial data API permission issue: {e}")
            return "permission"
        print(f"❌ Financial data test failed: {e}")
        return False


def test_config_files():
    """Test configuration files."""
    print("\n" + "=" * 60)
    print("Test 6: Configuration Files")
    print("=" * 60)

    try:
        from app.config.qlib import qlib_config

        print(f"✅ Qlib config loaded")
        print(f"   Source: {qlib_config.source}")
        print(f"   Stock pool: {qlib_config.stock_pool}")
        print(f"   Region: {qlib_config.region}")
        print(f"   Freq: {qlib_config.freq}")

        # Check if source is tushare
        if qlib_config.source == "tushare":
            print(f"✅ Data source correctly set to 'tushare'")
            return True
        else:
            print(f"❌ Data source is '{qlib_config.source}', expected 'tushare'")
            return False

    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False


def test_index_config():
    """Test index configuration."""
    print("\n" + "=" * 60)
    print("Test 7: Index Configuration")
    print("=" * 60)

    try:
        from app.services.index_components_service import get_index_components_service

        service = get_index_components_service()

        # Get active index
        active_index = service.get_active_index()
        print(f"✅ Active index: {active_index}")

        # Get index config
        config = service.get_index_config(active_index)
        print(f"   Name: {config.get('name')}")
        print(f"   Components source: {config.get('components_source')}")
        print(f"   Components index code: {config.get('components_index_code')}")

        # Check if source is tushare
        if config.get("components_source") == "tushare":
            print(f"✅ Components source correctly set to 'tushare'")
            return True
        else:
            print(
                f"❌ Components source is '{config.get('components_source')}', expected 'tushare'"
            )
            return False

    except Exception as e:
        print(f"❌ Index config test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("QuantBot Data Source Configuration Test")
    print("=" * 60)

    results = []

    # Run tests (now with 2120 points - should have access to more APIs)
    results.append(("Tushare Connection", test_tushare_connection()))
    results.append(("Index Components", test_index_components()))
    results.append(("Trading Calendar", test_trading_calendar()))
    results.append(("Single Stock Data", test_single_stock_data()))
    results.append(("Financial Data", test_financial_data()))
    results.append(("Config Files", test_config_files()))
    results.append(("Index Config", test_index_config()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = 0
    failed = 0
    permission_issues = 0

    for name, result in results:
        if result == "permission":
            status = "⚠️ PERMISSION"
            permission_issues += 1
        elif result:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1
        print(f"  {name}: {status}")

    print(
        f"\nTotal: {passed} passed, {failed} failed, {permission_issues} permission issues"
    )

    if permission_issues > 0:
        print("\n⚠️ Some tests failed due to Tushare API permission restrictions.")
        print(
            "   Visit https://tushare.pro/document/1?doc_id=108 to check your points."
        )
        print("   Basic APIs (daily, trade_cal) require 120+ points.")
        print("   Advanced APIs (index_weight) require 2000+ points.")

    if failed == 0:
        print("\n🎉 All tests passed! Data source configuration is correct.")
        return 0
    else:
        print(f"\n⚠️ {failed} test(s) failed. Please check the configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
