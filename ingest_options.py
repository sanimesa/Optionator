import duckdb
import os
import json
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "options.db")
DATA_DIR = "/mnt/c/Development/Python/fingrow/data/option_chains/"

def init_db():
    con = duckdb.connect(DB_FILE)
    con.execute("""
        CREATE TABLE IF NOT EXISTS option_chains (
            ticker TEXT,
            expiry DATE,
            run_date TIMESTAMP,
            file_name TEXT,
            raw_json JSON,
            PRIMARY KEY (ticker, expiry, run_date)
        )
    """)
    con.close()
    print(f"Database {DB_FILE} initialized.")

def ingest_files():
    con = duckdb.connect(DB_FILE)
    
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")]
    
    for filename in files:
        # Expected format: TICKER_EXPIRY_option_chain_RUNDATE.json
        # e.g., COHR_2026-03-20_option_chain_2026-02-25.json
        
        try:
            parts = filename.replace(".json", "").split("_option_chain_")
            if len(parts) != 2:
                print(f"Skipping {filename}: unexpected format")
                continue
                
            left_parts = parts[0].split("_")
            ticker = left_parts[0]
            expiry_str = left_parts[1]
            run_date_str = parts[1]
            
            # Check if exists
            count = con.execute("SELECT count(*) FROM option_chains WHERE file_name = ?", [filename]).fetchone()[0]
            if count > 0:
                print(f"Skipping {filename}: already exists")
                continue
            
            file_path = os.path.join(DATA_DIR, filename)
            with open(file_path, 'r') as f:
                content = f.read()
                # Validate JSON
                json.loads(content)
                
            con.execute("INSERT INTO option_chains VALUES (?, ?, ?, ?, ?)", 
                        [ticker, expiry_str, run_date_str, filename, content])
            print(f"Ingested {filename}")
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    con.close()

if __name__ == "__main__":
    init_db()
    ingest_files()
