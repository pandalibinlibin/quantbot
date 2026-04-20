"""
Data-Factor Integration Test Script

This script tests the complete workflow from data collection to factor computation
in the Docker environment, ensuring proper integration between components.

Educational Notes:
- Designed to run inside Docker container
- Tests end-to-end workflow: data collection → factor computation
- Validates both full and incremental update modes
- Checks error handling and status reporting
"""

import sys
import os
import logging
import uuid
from pathlib import Path
from datetime import datetime
import json

# Add backend to Python path for imports
backend_path = Path("/app/backend")
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("DataFactorIntegrationTest")


def get_or_create_test_user():
    """Get or create a test user for factor creation"""
    try:
        from app.models import User
        from app.core.db import engine
        from sqlmodel import Session, select

        with Session(engine) as session:
            # Try to find an existing user
            statement = select(User).limit(1)
            user = session.exec(statement).first()

            if user:
                logger.info(f"Using existing user: {user.email}")
                return user.id
            else:
                # Create a test user if none exists
                test_user = User(
                    email="test@example.com", full_name="Test User", is_superuser=False
                )
                session.add(test_user)
                session.commit()
                session.refresh(test_user)
                logger.info(f"Created test user: {test_user.email}")
                return test_user.id

    except Exception as e:
        logger.error(f"Failed to get or create test user: {e}")
        # Return a dummy UUID if user creation fails
        return uuid.uuid4()


def setup_test_environment():
    """Setup test environment and create test factors"""
    logger.info("Setting up test environment...")

    try:
        from app.core.db import engine
        from app.models import Factor, FactorStatus
        from sqlmodel import Session, select

        logger.info("✓ Database connection established")

        # Get a user ID for factor creation
        user_id = get_or_create_test_user()

        # Create test factors
        test_factors = [
            {
                "name": "Daily_Return",
                "description": "Daily return factor for integration testing",
                "expression": "($close / Ref($close, 1)) - 1",
                "status": FactorStatus.ACTIVE,
                "created_by": user_id,
            },
            {
                "name": "MA5",
                "description": "5-day moving average for integration testing",
                "expression": "Mean($close, 5)",
                "status": FactorStatus.ACTIVE,
                "created_by": user_id,
            },
        ]

        with Session(engine) as session:
            for factor_data in test_factors:
                # Check if factor already exists
                statement = select(Factor).where(Factor.name == factor_data["name"])
                existing_factor = session.exec(statement).first()

                if not existing_factor:
                    factor = Factor(**factor_data)
                    session.add(factor)
                    logger.info(f"Created test factor: {factor_data['name']}")
                else:
                    # Update existing factor to ensure it's active
                    existing_factor.status = FactorStatus.ACTIVE
                    existing_factor.description = factor_data["description"]
                    existing_factor.expression = factor_data["expression"]
                    session.add(existing_factor)
                    logger.info(f"Updated existing factor: {factor_data['name']}")

            session.commit()
            logger.info("✓ Test factors created/updated")

        return True

    except Exception as e:
        logger.error(f"Failed to setup test environment: {e}")
        return False


def test_full_data_factor_integration():
    """Test full data collection + factor computation integration"""
    logger.info("=== Testing Full Data-Factor Integration ===")

    try:
        from app.models import DownloadDataRequest
        from app.services.data_collectors.pipeline.service import execute_data_pipeline

        # Create test request for full refresh
        test_request = DownloadDataRequest(
            stock_pool="csi300",
            start_date="2023-12-01",
            end_date="2023-12-05",  # Small date range for testing
            incremental=False,  # Full refresh
            interval="1d",
        )

        logger.info("Executing full data-factor integration test...")

        # Execute the complete pipeline
        result = execute_data_pipeline(test_request)

        # Analyze results
        success = result.status == "completed"
        factor_triggered = "Factor computation:" in result.message

        logger.info(f"Pipeline Status: {result.status}")
        logger.info(f"Pipeline Message: {result.message}")

        if success:
            logger.info("✓ Full data-factor integration test PASSED")
            if factor_triggered:
                logger.info("✓ Factor computation was triggered successfully")
            else:
                logger.warning("⚠ Factor computation may not have been triggered")
        else:
            logger.error(
                f"✗ Full data-factor integration test FAILED: {result.message}"
            )

        return {
            "test_name": "full_data_factor_integration",
            "success": success,
            "factor_triggered": factor_triggered,
            "status": result.status,
            "message": result.message,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Full data-factor integration test failed with exception: {e}")
        return {
            "test_name": "full_data_factor_integration",
            "success": False,
            "factor_triggered": False,
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def test_incremental_data_factor_integration():
    """Test incremental data collection + factor computation integration"""
    logger.info("=== Testing Incremental Data-Factor Integration ===")

    try:
        from app.models import DownloadDataRequest
        from app.services.data_collectors.pipeline.service import execute_data_pipeline

        # Create test request for incremental update
        test_request = DownloadDataRequest(
            stock_pool="csi300",
            start_date="2023-12-06",
            end_date="2023-12-08",  # Extended date range
            incremental=True,  # Incremental update
            interval="1d",
        )

        logger.info("Executing incremental data-factor integration test...")

        # Execute the complete pipeline
        result = execute_data_pipeline(test_request)

        # Analyze results
        success = result.status == "completed"
        factor_triggered = "Factor computation:" in result.message

        logger.info(f"Pipeline Status: {result.status}")
        logger.info(f"Pipeline Message: {result.message}")

        if success:
            logger.info("✓ Incremental data-factor integration test PASSED")
            if factor_triggered:
                logger.info(
                    "✓ Incremental factor computation was triggered successfully"
                )
            else:
                logger.warning(
                    "⚠ Incremental factor computation may not have been triggered"
                )
        else:
            logger.error(
                f"✗ Incremental data-factor integration test FAILED: {result.message}"
            )

        return {
            "test_name": "incremental_data_factor_integration",
            "success": success,
            "factor_triggered": factor_triggered,
            "status": result.status,
            "message": result.message,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(
            f"Incremental data-factor integration test failed with exception: {e}"
        )
        return {
            "test_name": "incremental_data_factor_integration",
            "success": False,
            "factor_triggered": False,
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def check_factor_data_consistency():
    """Check if factor data was properly stored"""
    logger.info("=== Checking Factor Data Consistency ===")

    try:
        from app.services.factor_storage import FactorStorage

        storage = FactorStorage(freq="day")

        # Check if factor data exists
        factor_names = ["Daily_Return", "MA5"]
        consistency_results = []

        for factor_name in factor_names:
            try:
                # Try to load factor data
                factor_data = storage.load_factor_data(
                    factor_name=factor_name,
                    start_time="2023-12-01",
                    end_time="2023-12-08",
                )

                if factor_data is not None and not factor_data.empty:
                    logger.info(
                        f"✓ Factor '{factor_name}' data found: {factor_data.shape}"
                    )
                    consistency_results.append(
                        {
                            "factor_name": factor_name,
                            "data_exists": True,
                            "data_shape": factor_data.shape,
                            "date_range": f"{factor_data.index.min()} to {factor_data.index.max()}",
                        }
                    )
                else:
                    logger.warning(f"⚠ Factor '{factor_name}' data not found or empty")
                    consistency_results.append(
                        {
                            "factor_name": factor_name,
                            "data_exists": False,
                            "data_shape": None,
                            "date_range": None,
                        }
                    )

            except Exception as e:
                logger.error(f"✗ Failed to load factor '{factor_name}': {e}")
                consistency_results.append(
                    {"factor_name": factor_name, "data_exists": False, "error": str(e)}
                )

        return {
            "test_name": "factor_data_consistency",
            "results": consistency_results,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Factor data consistency check failed: {e}")
        return {
            "test_name": "factor_data_consistency",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def check_database_factor_status():
    """Check factor status in database"""
    logger.info("=== Checking Database Factor Status ===")

    try:
        from app.models import Factor, FactorStatus
        from app.core.db import engine
        from sqlmodel import Session, select

        with Session(engine) as session:
            statement = select(Factor).where(Factor.status == FactorStatus.ACTIVE)
            active_factors = session.exec(statement).all()

            factor_info = []
            for factor in active_factors:
                factor_info.append(
                    {
                        "name": factor.name,
                        "status": factor.status,
                        "expression": factor.expression,
                        "description": factor.description,
                    }
                )
                logger.info(f"✓ Active factor found: {factor.name}")

            logger.info(f"Total active factors: {len(active_factors)}")

            return {
                "test_name": "database_factor_status",
                "active_factors_count": len(active_factors),
                "factors": factor_info,
                "timestamp": datetime.now().isoformat(),
            }

    except Exception as e:
        logger.error(f"Database factor status check failed: {e}")
        return {
            "test_name": "database_factor_status",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def check_qlib_data_structure():
    """Check if Qlib data structure was created properly"""
    logger.info("=== Checking Qlib Data Structure ===")

    try:
        from app.core.config import settings

        qlib_data_path = Path(settings.QLIB_DATA_PATH)
        structure_info = {
            "qlib_data_exists": qlib_data_path.exists(),
            "features_dir_exists": False,
            "calendars_dir_exists": False,
            "instruments_dir_exists": False,
            "bin_files_count": 0,
            "directories": [],
        }

        if qlib_data_path.exists():
            logger.info(f"✓ Qlib data directory exists: {qlib_data_path}")

            # Check subdirectories
            for subdir in qlib_data_path.iterdir():
                if subdir.is_dir():
                    structure_info["directories"].append(subdir.name)

                    if subdir.name == "features":
                        structure_info["features_dir_exists"] = True
                        # Count bin files
                        bin_files = list(subdir.rglob("*.bin"))
                        structure_info["bin_files_count"] = len(bin_files)
                        logger.info(
                            f"✓ Features directory found with {len(bin_files)} .bin files"
                        )

                    elif subdir.name == "calendars":
                        structure_info["calendars_dir_exists"] = True
                        logger.info("✓ Calendars directory found")

                    elif subdir.name == "instruments":
                        structure_info["instruments_dir_exists"] = True
                        logger.info("✓ Instruments directory found")
        else:
            logger.warning(f"⚠ Qlib data directory not found: {qlib_data_path}")

        return {
            "test_name": "qlib_data_structure",
            "structure_info": structure_info,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Qlib data structure check failed: {e}")
        return {
            "test_name": "qlib_data_structure",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def check_factor_pipeline_components():
    """Check if factor pipeline components are working"""
    logger.info("=== Checking Factor Pipeline Components ===")

    try:
        from app.services.factor_pipeline import FactorPipeline, UpdateMode

        # Initialize factor pipeline
        pipeline = FactorPipeline(freq="day", max_workers=2)

        # Get pipeline status
        status = pipeline.get_pipeline_status()

        logger.info("✓ Factor pipeline initialized successfully")
        logger.info(
            f"Pipeline type: {status.get('pipeline_info', {}).get('type', 'unknown')}"
        )
        logger.info(
            f"Pipeline strategy: {status.get('pipeline_info', {}).get('strategy', 'unknown')}"
        )

        # Check components
        components = status.get("pipeline_info", {}).get("components", {})
        for component_name, component_class in components.items():
            logger.info(f"✓ Component '{component_name}': {component_class}")

        return {
            "test_name": "factor_pipeline_components",
            "pipeline_status": status,
            "components_count": len(components),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Factor pipeline components check failed: {e}")
        return {
            "test_name": "factor_pipeline_components",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def main():
    """Main test execution function"""
    logger.info("🚀 Starting Data-Factor Integration Tests")

    # Test results collection
    all_results = []

    # Step 1: Setup test environment
    if not setup_test_environment():
        logger.error("Failed to setup test environment, aborting tests")
        return 1

    # Step 2: Check database factor status
    db_status_result = check_database_factor_status()
    all_results.append(db_status_result)

    # Step 3: Check factor pipeline components
    pipeline_components_result = check_factor_pipeline_components()
    all_results.append(pipeline_components_result)

    # Step 4: Test full integration
    full_test_result = test_full_data_factor_integration()
    all_results.append(full_test_result)

    # Step 5: Test incremental integration
    incremental_test_result = test_incremental_data_factor_integration()
    all_results.append(incremental_test_result)

    # Step 6: Check Qlib data structure
    qlib_structure_result = check_qlib_data_structure()
    all_results.append(qlib_structure_result)

    # Step 7: Check factor data consistency
    consistency_result = check_factor_data_consistency()
    all_results.append(consistency_result)

    # Step 8: Generate test report
    logger.info("=== Integration Test Summary ===")

    passed_tests = 0
    total_tests = 0

    for result in all_results:
        if "success" in result:
            total_tests += 1
            if result["success"]:
                passed_tests += 1
                logger.info(f"✓ {result['test_name']}: PASSED")
            else:
                logger.error(f"✗ {result['test_name']}: FAILED")
        else:
            # Non-success/failure tests (info checks)
            logger.info(f"ℹ {result['test_name']}: INFO CHECK COMPLETED")

    logger.info(f"Test Results: {passed_tests}/{total_tests} tests passed")

    # Save detailed results to file
    results_file = Path("/app/temp_scripts/integration_test_results.json")
    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    logger.info(f"Detailed results saved to: {results_file}")

    # Print summary information
    logger.info("=== Test Summary Details ===")
    for result in all_results:
        if result["test_name"] == "database_factor_status":
            logger.info(
                f"Active factors in database: {result.get('active_factors_count', 0)}"
            )
        elif result["test_name"] == "factor_pipeline_components":
            logger.info(
                f"Factor pipeline components: {result.get('components_count', 0)}"
            )
        elif result["test_name"] == "qlib_data_structure":
            structure = result.get("structure_info", {})
            logger.info(
                f"Qlib data structure: {structure.get('bin_files_count', 0)} .bin files found"
            )
        elif result["test_name"] == "factor_data_consistency":
            results_list = result.get("results", [])
            data_found = sum(1 for r in results_list if r.get("data_exists", False))
            logger.info(
                f"Factor data consistency: {data_found}/{len(results_list)} factors have data"
            )

    if passed_tests == total_tests and total_tests > 0:
        logger.info("🎉 All integration tests PASSED!")
        return 0
    elif total_tests == 0:
        logger.warning("⚠ No tests were executed")
        return 1
    else:
        logger.error(f"❌ {total_tests - passed_tests} integration tests FAILED!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
