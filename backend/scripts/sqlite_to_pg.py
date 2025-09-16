#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script
Migrates data from local SQLite to PostgreSQL (development use only)
"""
import os
import sys
import sqlite3
import argparse
from typing import Dict, List, Any

def get_sqlite_data(db_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """Extract all data from SQLite database"""
    if not os.path.exists(db_path):
        print(f"❌ SQLite database not found: {db_path}")
        return {}
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    data = {}
    
    try:
        # Get all tables
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in cursor.fetchall()]
        
        print(f"📋 Found {len(tables)} tables: {', '.join(tables)}")
        
        for table in tables:
            if table == 'sqlite_sequence':  # Skip SQLite internal table
                continue
                
            cursor = conn.execute(f"SELECT * FROM {table}")
            rows = [dict(row) for row in cursor.fetchall()]
            data[table] = rows
            print(f"  📊 {table}: {len(rows)} rows")
            
    except Exception as e:
        print(f"❌ Error reading SQLite data: {e}")
        return {}
    finally:
        conn.close()
    
    return data

def migrate_to_postgres(data: Dict[str, List[Dict[str, Any]]], pg_url: str):
    """Migrate data to PostgreSQL"""
    try:
        from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Integer, DateTime, Boolean, Text
        from sqlalchemy.dialects.postgresql import JSONB
        from sqlalchemy.orm import sessionmaker
        from datetime import datetime
        import json
        
        # Create PostgreSQL engine
        engine = create_engine(pg_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        print(f"🔗 Connected to PostgreSQL")
        
        # Create tables and migrate data
        for table_name, rows in data.items():
            if not rows:
                continue
                
            print(f"🔄 Migrating table: {table_name}")
            
            # Create table if it doesn't exist
            try:
                # Simple table creation based on first row
                if rows:
                    first_row = rows[0]
                    columns = []
                    
                    for col_name, value in first_row.items():
                        if isinstance(value, bool):
                            col_type = Boolean
                        elif isinstance(value, int):
                            col_type = Integer
                        elif isinstance(value, datetime):
                            col_type = DateTime
                        elif isinstance(value, dict) or isinstance(value, list):
                            col_type = JSONB
                        else:
                            col_type = Text
                        
                        columns.append(Column(col_name, col_type))
                    
                    # Create table
                    metadata = MetaData()
                    table = Table(table_name, metadata, *columns)
                    metadata.create_all(engine)
                    print(f"  ✅ Created table: {table_name}")
                    
                    # Insert data
                    for row in rows:
                        # Convert SQLite row to dict, handling JSON
                        insert_data = {}
                        for key, value in row.items():
                            if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                                try:
                                    insert_data[key] = json.loads(value)
                                except:
                                    insert_data[key] = value
                            else:
                                insert_data[key] = value
                        
                        # Insert row
                        try:
                            session.execute(table.insert().values(**insert_data))
                        except Exception as e:
                            print(f"  ⚠️  Warning: Could not insert row in {table_name}: {e}")
                            continue
                    
                    session.commit()
                    print(f"  ✅ Migrated {len(rows)} rows to {table_name}")
                    
            except Exception as e:
                print(f"  ❌ Error migrating table {table_name}: {e}")
                session.rollback()
                continue
        
        session.close()
        print("✅ Migration completed successfully")
        
    except ImportError:
        print("❌ SQLAlchemy not available. Install with: pip install sqlalchemy psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Error connecting to PostgreSQL: {e}")
        return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Migrate SQLite data to PostgreSQL')
    parser.add_argument('--sqlite', default='./instance/app.db', help='SQLite database path')
    parser.add_argument('--postgres', required=True, help='PostgreSQL connection URL')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated without doing it')
    
    args = parser.parse_args()
    
    print("🚀 SQLite to PostgreSQL Migration Tool")
    print(f"   SQLite: {args.sqlite}")
    print(f"   PostgreSQL: {args.postgres}")
    print()
    
    # Extract data from SQLite
    data = get_sqlite_data(args.sqlite)
    
    if not data:
        print("❌ No data found to migrate")
        sys.exit(1)
    
    if args.dry_run:
        print("🔍 DRY RUN - Would migrate:")
        for table, rows in data.items():
            print(f"  {table}: {len(rows)} rows")
        print("✅ Dry run completed")
        return
    
    # Migrate to PostgreSQL
    success = migrate_to_postgres(data, args.postgres)
    
    if success:
        print("🎉 Migration completed successfully!")
    else:
        print("❌ Migration failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
