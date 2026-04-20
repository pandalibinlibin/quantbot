#!/usr/bin/env python3
"""
Factor Integration Test Script

This script tests the integration between our factor management system and Qlib.
It should be run inside the Docker container to have access to the database and Qlib.
"""

import logging
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_factor_loading():
    """Test if CustomFactorHandler can load factors from database"""
    logger.info("=== Testing Database Factor Loading ===")
    
    try:
        from app.services.custom_factor_handler import CustomFactorHandler
        
        # Create handler with database integration enabled
        logger.info("Creating CustomFactorHandler with database integration...")
        handler = CustomFactorHandler(
            instruments="csi300",
            start_time="2020-01-01",
            end_time="2021-01-01",
            enable_alpha158=False  # Only test custom factors
        )
        
        # Test the _load_custom_factors_from_db method directly
        logger.info("Loading custom factors from database...")
        custom_factors = handler._load_custom_factors_from_db()
        
        if custom_factors:
            logger.info(f"Successfully loaded {len(custom_factors)} custom factors:")
            for factor in custom_factors:
                logger.info(f"  - {factor['name']}: {factor['expression']}")
            return True
        else:
            logger.warning("No custom factors found in database")
            return False
            
    except Exception as e:
        logger.error(f"Failed to load factors from database: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting Factor-Qlib Integration Tests")
    logger.info("=" * 50)
    
    # Test database factor loading
    result = test_database_factor_loading()
    
    if result:
        logger.info("Integration test passed!")
        sys.exit(0)
    else:
        logger.error("Integration test failed!")
        sys.exit(1)