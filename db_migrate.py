#!/usr/bin/env python3
"""
Database migration and management script for soft_batch.
"""
import os
import sqlite3
from datetime import datetime
from database import init_db, get_schema_info, get_stats, DEFAULT_DB_PATH


def check_db_exists(db_path: str = DEFAULT_DB_PATH) -> bool:
    """Check if database file exists."""
    return os.path.exists(db_path)


def backup_db(db_path: str = DEFAULT_DB_PATH) -> str:
    """Create a backup of the database."""
    if not check_db_exists(db_path):
        print("[-] No database to backup")
        return ""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"

    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"[+] Backup created: {backup_path}")
    return backup_path


def show_tables(db_path: str = DEFAULT_DB_PATH):
    """Show all tables and their row counts."""
    if not check_db_exists(db_path):
        print("[-] Database does not exist. Run 'init' first.")
        return

    schema_info = get_schema_info(db_path)

    print("\n" + "="*60)
    print("DATABASE TABLES")
    print("="*60)

    with sqlite3.connect(db_path) as conn:
        for table_name in schema_info["tables"].keys():
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  [TABLE] {table_name:<20} {count:>10} rows")

    print("\n" + "="*60)
    print("INDICES")
    print("="*60)
    for idx_name, tbl_name, _ in schema_info["indices"]:
        print(f"  [INDEX] {idx_name:<30} -> {tbl_name}")

    print("\n" + "="*60)
    print("VIEWS")
    print("="*60)
    for view_name in schema_info["views"].keys():
        print(f"  [VIEW] {view_name}")
    print()


def show_detailed_stats(db_path: str = DEFAULT_DB_PATH):
    """Show detailed database statistics."""
    if not check_db_exists(db_path):
        print("[-] Database does not exist. Run 'init' first.")
        return

    stats = get_stats(db_path)

    print("\n" + "="*60)
    print("DATABASE STATISTICS")
    print("="*60)

    print(f"\nArticles:")
    print(f"  Total articles: {stats['total_articles']}")
    print(f"  Unique sources: {stats['unique_sources']}")
    print(f"  New (last 7 days): {stats['new_articles_last_7_days']}")

    print(f"\nPosts:")
    for status, count in stats.get('posts_by_status', {}).items():
        print(f"  {status.capitalize()}: {count}")
    print(f"  Created (last 7 days): {stats['posts_last_7_days']}")

    print(f"\nComments:")
    for status, count in stats.get('comments_by_status', {}).items():
        print(f"  {status.capitalize()}: {count}")

    print()


def query_interactive(db_path: str = DEFAULT_DB_PATH):
    """Interactive SQL query interface."""
    if not check_db_exists(db_path):
        print("[-] Database does not exist. Run 'init' first.")
        return

    print("\n" + "="*60)
    print("INTERACTIVE SQL QUERY")
    print("="*60)
    print("Enter SQL queries. Type 'exit' to quit.\n")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        while True:
            try:
                query = input("SQL> ").strip()

                if query.lower() in ('exit', 'quit'):
                    break

                if not query:
                    continue

                cursor = conn.execute(query)

                # For SELECT queries
                if query.lower().startswith('select'):
                    rows = cursor.fetchall()
                    if rows:
                        # Print column names
                        print("\n" + " | ".join(rows[0].keys()))
                        print("-" * 60)
                        # Print rows
                        for row in rows:
                            print(" | ".join(str(v) for v in row))
                        print(f"\n{len(rows)} row(s) returned\n")
                    else:
                        print("No results.\n")
                else:
                    # For INSERT/UPDATE/DELETE
                    conn.commit()
                    print(f"[+] Query executed. {cursor.rowcount} row(s) affected.\n")

            except sqlite3.Error as e:
                print(f"[-] SQL Error: {e}\n")
            except KeyboardInterrupt:
                print("\nExiting...\n")
                break


def main():
    """Main CLI interface."""
    import sys

    if len(sys.argv) < 2:
        print("""
Database Migration & Management Tool

Usage:
  python db_migrate.py init       - Initialize/create database
  python db_migrate.py backup     - Create database backup
  python db_migrate.py tables     - Show all tables and indices
  python db_migrate.py stats      - Show detailed statistics
  python db_migrate.py query      - Interactive SQL query interface
  python db_migrate.py schema     - Show full schema SQL
        """)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "init":
        if check_db_exists():
            response = input(f"[!] Database already exists at {DEFAULT_DB_PATH}. Reinitialize? (y/N): ")
            if response.lower() != 'y':
                print("Aborted.")
                sys.exit(0)
            backup_db()
        init_db()
        show_tables()

    elif command == "backup":
        backup_db()

    elif command == "tables":
        show_tables()

    elif command == "stats":
        show_detailed_stats()

    elif command == "query":
        query_interactive()

    elif command == "schema":
        schema_info = get_schema_info()
        print("\n" + "="*60)
        print("DATABASE SCHEMA")
        print("="*60)
        for name, sql in schema_info["tables"].items():
            print(f"\n-- Table: {name}")
            print(sql)
            print()

    else:
        print(f"[-] Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
