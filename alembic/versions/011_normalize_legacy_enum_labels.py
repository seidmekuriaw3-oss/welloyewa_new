"""Normalize legacy uppercase PostgreSQL enum labels.

Revision ID: 011_normalize_legacy_enum_labels
Revises: 010_repair_legacy_model_columns
"""

from alembic import op


revision = "011_normalize_legacy_enum_labels"
down_revision = "010_repair_legacy_model_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            enum_value RECORD;
            lowercase_label TEXT;
        BEGIN
            FOR enum_value IN
                SELECT type_namespace.nspname AS schema_name,
                       enum_type.typname AS type_name,
                       enum_label.enumlabel AS label
                FROM pg_type AS enum_type
                JOIN pg_enum AS enum_label ON enum_label.enumtypid = enum_type.oid
                JOIN pg_namespace AS type_namespace
                  ON type_namespace.oid = enum_type.typnamespace
                WHERE type_namespace.nspname = current_schema()
                  AND enum_type.typtype = 'e'
                  AND enum_label.enumlabel <> lower(enum_label.enumlabel)
            LOOP
                lowercase_label := lower(enum_value.label);

                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_type AS enum_type
                    JOIN pg_enum AS enum_label ON enum_label.enumtypid = enum_type.oid
                    JOIN pg_namespace AS type_namespace
                      ON type_namespace.oid = enum_type.typnamespace
                    WHERE type_namespace.nspname = enum_value.schema_name
                      AND enum_type.typname = enum_value.type_name
                      AND enum_label.enumlabel = lowercase_label
                ) THEN
                    EXECUTE format(
                        'ALTER TYPE %I.%I RENAME VALUE %L TO %L',
                        enum_value.schema_name,
                        enum_value.type_name,
                        enum_value.label,
                        lowercase_label
                    );
                END IF;
            END LOOP;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            enum_value RECORD;
            uppercase_label TEXT;
        BEGIN
            FOR enum_value IN
                SELECT type_namespace.nspname AS schema_name,
                       enum_type.typname AS type_name,
                       enum_label.enumlabel AS label
                FROM pg_type AS enum_type
                JOIN pg_enum AS enum_label ON enum_label.enumtypid = enum_type.oid
                JOIN pg_namespace AS type_namespace
                  ON type_namespace.oid = enum_type.typnamespace
                WHERE type_namespace.nspname = current_schema()
                  AND enum_type.typtype = 'e'
                  AND enum_label.enumlabel = lower(enum_label.enumlabel)
            LOOP
                uppercase_label := upper(enum_value.label);

                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_type AS enum_type
                    JOIN pg_enum AS enum_label ON enum_label.enumtypid = enum_type.oid
                    JOIN pg_namespace AS type_namespace
                      ON type_namespace.oid = enum_type.typnamespace
                    WHERE type_namespace.nspname = enum_value.schema_name
                      AND enum_type.typname = enum_value.type_name
                      AND enum_label.enumlabel = uppercase_label
                ) THEN
                    EXECUTE format(
                        'ALTER TYPE %I.%I RENAME VALUE %L TO %L',
                        enum_value.schema_name,
                        enum_value.type_name,
                        enum_value.label,
                        uppercase_label
                    );
                END IF;
            END LOOP;
        END
        $$;
        """
    )
