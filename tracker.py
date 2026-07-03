import sqlite3
from datetime import datetime

DB_PATH = "./data/onboard.db"

def init_db():
    """Initialize the database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            question TEXT NOT NULL,
            topic TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS volunteers (
            user_id TEXT PRIMARY KEY,
            first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_questions INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized.")

def log_interaction(user_id, question, topic=None):
    """Log a volunteer's question"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO interactions (user_id, question, topic)
        VALUES (?, ?, ?)
    ''', (user_id, question, topic))
    
    c.execute('''
        INSERT INTO volunteers (user_id, total_questions, last_active)
        VALUES (?, 1, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            total_questions = total_questions + 1,
            last_active = ?
    ''', (user_id, datetime.now().isoformat(), datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def get_volunteer_stats(user_id):
    """Get stats for a specific volunteer"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        SELECT total_questions, first_seen, last_active
        FROM volunteers WHERE user_id = ?
    ''', (user_id,))
    volunteer = c.fetchone()
    
    if not volunteer:
        conn.close()
        return None
    
    total_questions, first_seen, last_active = volunteer
    
    c.execute('''
        SELECT DISTINCT topic FROM interactions
        WHERE user_id = ? AND topic IS NOT NULL
        ORDER BY timestamp DESC LIMIT 5
    ''', (user_id,))
    topics = [row[0] for row in c.fetchall()]
    
    c.execute('''
        SELECT question, timestamp FROM interactions
        WHERE user_id = ?
        ORDER BY timestamp DESC LIMIT 3
    ''', (user_id,))
    recent = c.fetchall()
    
    conn.close()
    
    return {
        "total_questions": total_questions,
        "first_seen": first_seen,
        "last_active": last_active,
        "topics": topics,
        "recent_questions": recent
    }

def detect_topic(question):
    """Simple topic detection from question"""
    question_lower = question.lower()
    if any(w in question_lower for w in ["orientation", "register", "start", "begin", "join"]):
        return "Getting Started"
    elif any(w in question_lower for w in ["program", "education", "food", "health", "tutor"]):
        return "Programs"
    elif any(w in question_lower for w in ["policy", "policies", "badge", "commit", "hours", "notice"]):
        return "Policies"
    elif any(w in question_lower for w in ["contact", "email", "phone", "sarah", "coordinator"]):
        return "Contact"
    else:
        return "General"

def get_all_volunteers():
    """Get all volunteer user IDs"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_id FROM volunteers')
    volunteers = [row[0] for row in c.fetchall()]
    conn.close()
    return volunteers

if __name__ == "__main__":
    init_db()
    log_interaction("U123", "When is orientation?", "Getting Started")
    log_interaction("U123", "What programs are available?", "Programs")
    stats = get_volunteer_stats("U123")
    print("Test stats:", stats)