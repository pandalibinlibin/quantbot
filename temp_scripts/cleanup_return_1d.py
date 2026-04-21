"""
Cleanup script: Remove the legacy 'return_1d' LABEL factor from DB and bin files.

Background:
- 'return_1d' was previously created as a LABEL factor (factor_type=label)
- The actual training label now comes from system_config.yaml (Ref($close, -2)/$close - 1)
- 'return_1d' = Ref($close, -1)/$close - 1 contains FUTURE data, cannot be used as feature
- This script removes the stale DB record and deletes the bin files

Usage:
    docker exec quantbot-backend-1 python /app/temp_scripts/cleanup_return_1d.py
"""

import sys
sys.path.insert(0, "/app")

def main():
    print("=" * 60)
    print("Cleanup: Remove legacy 'return_1d' LABEL factor")
    print("=" * 60)

    # Step 1: Check DB for return_1d
    print("\n[Step 1] Checking database for LABEL factors...")
    try:
        from sqlmodel import Session, select
        from app.core.db import engine
        from app.models import Factor, FactorType, FactorStatus

        with Session(engine) as session:
            # Find all LABEL type factors
            label_factors = session.exec(
                select(Factor).where(Factor.factor_type == FactorType.LABEL)
            ).all()

            if not label_factors:
                print("  No LABEL factors found in DB. Nothing to clean.")
            else:
                for f in label_factors:
                    print("  Found LABEL factor:")
                    print("    id:         " + str(f.id))
                    print("    name:       " + f.name)
                    print("    expression: " + str(f.expression))
                    print("    status:     " + str(f.status))
                    print("    type:       " + str(f.factor_type))

            # Find return_1d specifically
            return_1d = session.exec(
                select(Factor).where(Factor.name == "return_1d")
            ).first()

            if return_1d:
                print("\n  Deleting 'return_1d' from DB...")
                session.delete(return_1d)
                session.commit()
                print("  DB record deleted successfully.")
            else:
                print("\n  'return_1d' not found in DB. Skipping DB cleanup.")

    except Exception as e:
        print("  DB cleanup error: " + str(e))

    # Step 2: Delete return_1d bin files
    print("\n[Step 2] Deleting return_1d bin files from storage...")
    try:
        from app.services.factor_storage import FactorStorage

        storage = FactorStorage(freq="day")
        result = storage.delete_factor_data("return_1d")
        if result:
            print("  Bin files deleted successfully.")
        else:
            print("  No bin files found or deletion failed.")

    except Exception as e:
        print("  Bin file cleanup error: " + str(e))

    # Step 3: Verify cleanup
    print("\n[Step 3] Verifying cleanup...")
    try:
        from sqlmodel import Session, select
        from app.core.db import engine
        from app.models import Factor, FactorType

        with Session(engine) as session:
            remaining = session.exec(
                select(Factor).where(Factor.factor_type == FactorType.LABEL)
            ).all()
            if remaining:
                print("  WARNING: Still have LABEL factors in DB:")
                for f in remaining:
                    print("    - " + f.name + " (" + str(f.status) + ")")
            else:
                print("  No LABEL factors remain in DB.")

        storage = FactorStorage(freq="day")
        stored = storage.list_stored_factors()
        if "return_1d" in stored:
            print("  WARNING: return_1d still found in stored factors!")
        else:
            print("  return_1d not found in stored factors. Clean!")

        print("\n  Current stored factors: " + str(stored))

    except Exception as e:
        print("  Verification error: " + str(e))

    print("\n" + "=" * 60)
    print("Cleanup complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
