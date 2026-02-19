"""add_factor_type_field

Revision ID: c9990fb7c538
Revises: 1e5153956860
Create Date: 2026-02-19 07:55:49.574810

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = "c9990fb7c538"
down_revision = "1e5153956860"
branch_labels = None
depends_on = None


def upgrade():
    # Create the factortype enum type first
    factortype_enum = sa.Enum("FEATURE", "LABEL", name="factortype")
    factortype_enum.create(op.get_bind(), checkfirst=True)

    # Add factor_type column with default value for existing rows
    op.add_column("factor", sa.Column("factor_type", factortype_enum, nullable=True))

    # Set default value for existing rows
    op.execute("UPDATE factor SET factor_type = 'FEATURE' WHERE factor_type IS NULL")

    # Make the column non-nullable
    op.alter_column("factor", "factor_type", nullable=False)


def downgrade():
    op.drop_column("factor", "factor_type")

    # Drop the enum type
    factortype_enum = sa.Enum("FEATURE", "LABEL", name="factortype")
    factortype_enum.drop(op.get_bind(), checkfirst=True)
