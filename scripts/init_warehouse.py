
from pathlib import Path

import duckdb

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "retailpulse.duckdb"
SCHEMA_PATH = BASE_DIR / "sql" / "schema.sql"


def initialize_warehouse():
    """Create the DuckDB database and initialize its schema."""

    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"Schema file not found: {SCHEMA_PATH}"
        )

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    print("Initializing RetailPulse warehouse...")

    with duckdb.connect(str(DATABASE_PATH)) as connection:
        connection.execute(schema_sql)

        tables = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        ).fetchall()

    print("\nWarehouse initialized successfully.")
    print(f"Database: {DATABASE_PATH}")
    print("\nCreated tables:")

    for table in tables:
        print(f"  - {table[0]}")


if __name__ == "__main__":
    initialize_warehouse()
