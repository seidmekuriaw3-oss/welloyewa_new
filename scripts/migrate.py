"""Command-line entry point for database migrations."""

import sys

from alembic.config import main as alembic_main


def main() -> None:
    """Run Alembic with arguments passed to the installed ``migrate`` command."""
    alembic_main(sys.argv[1:], prog="migrate")


if __name__ == "__main__":
    main()
