import sqlite3
import os
from datetime import datetime

# Lokasi file database akan dibuat di folder backend
DB_PATH = os.path.join(os.path.dirname(__file__), "mata_warga.db")

def init_db():
    """Membuat tabel database jika belum ada."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            violation_type TEXT NOT NULL,
            plate_number TEXT,
            location_lat REAL,
            location_lng REAL,
            photo_path TEXT NOT NULL,
            ai_confidence REAL,
            ai_reason TEXT,
            status TEXT DEFAULT 'pending',
            reward_amount INTEGER DEFAULT 0,
            created_at TEXT,
            validated_at TEXT,
            note TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_report(violation_type, plate_number, lat, lng, photo_path, ai_confidence, ai_reason):
    """Menyimpan laporan baru dari warga."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO reports (violation_type, plate_number, location_lat, location_lng,
                             photo_path, ai_confidence, ai_reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (violation_type, plate_number, lat, lng, photo_path, ai_confidence, ai_reason,
          datetime.now().isoformat()))
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid

def get_reports(status=None):
    """Mengambil semua laporan (bisa difilter berdasarkan status)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if status:
        c.execute("SELECT * FROM reports WHERE status=? ORDER BY id DESC", (status,))
    else:
        c.execute("SELECT * FROM reports ORDER BY id DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_report(rid):
    """Mengambil detail satu laporan berdasarkan ID."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM reports WHERE id=?", (rid,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def update_status(rid, status, reward_amount=0, note=""):
    """Mengubah status laporan (validasi dari Polisi)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE reports 
        SET status=?, reward_amount=?, note=?, validated_at=? 
        WHERE id=?
    """, (status, reward_amount, note, datetime.now().isoformat(), rid))
    conn.commit()
    conn.close()

def get_stats():
    """Mengambil ringkasan data untuk ditampilkan di statistik website."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM reports")
    total = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM reports WHERE status='valid'")
    valid = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM reports WHERE status='rejected'")
    rejected = c.fetchone()[0]
    
    c.execute("SELECT SUM(reward_amount) FROM reports WHERE status='valid'")
    total_reward = c.fetchone()[0] or 0
    
    conn.close()
    return {
        "total": total, 
        "valid": valid, 
        "rejected": rejected,
        "pending": total - valid - rejected, 
        "total_reward": total_reward
    }