import sqlite3
from pathlib import Path

if __name__ == "__main__":
    con = sqlite3.connect(Path(__file__).parents[1].resolve() / "src" / "cards.db")
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS cards (name TEXT NOT NULL, setCode TEXT NOT NULL, collNo INTEGER NOT NULL, regMark TEXT NOT NULL, type TEXT NOT NULL, isStandardLegal BOOLEAN NOT NULL CHECK (isStandardLegal IN (0, 1)), isExpandedLegal BOOLEAN NOT NULL CHECK (isExpandedLegal IN (0, 1)))")
    con.commit()
    con.close()