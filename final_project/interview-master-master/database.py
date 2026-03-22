import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'interview_master.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # ---- Users Table ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'Candidate',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migration: Add role column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'Candidate'")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # ---- Interviews Table ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_role TEXT NOT NULL,
            company TEXT NOT NULL,
            interview_type TEXT NOT NULL,
            total_questions INTEGER DEFAULT 0,
            score REAL DEFAULT 0,
            rating TEXT DEFAULT '',
            feedback TEXT DEFAULT '',
            strengths TEXT DEFAULT '[]',
            weaknesses TEXT DEFAULT '[]',
            suggestions TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # ---- Questions Table ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interview_id INTEGER NOT NULL,
            question_number INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            category TEXT NOT NULL,
            difficulty TEXT DEFAULT 'Medium',
            user_answer TEXT DEFAULT '',
            ai_feedback TEXT DEFAULT '',
            score REAL DEFAULT 0,
            FOREIGN KEY (interview_id) REFERENCES interviews(id)
        )
    ''')

    # ---- Resumes Table (with extracted skills) ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            extracted_text TEXT DEFAULT '',
            extracted_skills TEXT DEFAULT '[]',
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # ---- Performance Details Table (stores detailed AI feedback per interview) ----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS performance_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interview_id INTEGER NOT NULL UNIQUE,
            technical_score REAL DEFAULT 0,
            hr_score REAL DEFAULT 0,
            communication_score REAL DEFAULT 0,
            confidence_score REAL DEFAULT 0,
            skill_gaps TEXT DEFAULT '[]',
            learning_resources TEXT DEFAULT '[]',
            improvement_roadmap TEXT DEFAULT '[]',
            weak_question_types TEXT DEFAULT '[]',
            strong_question_types TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (interview_id) REFERENCES interviews(id)
        )
    ''')

    # Add extracted_skills column to resumes if it doesn't exist (migration)
    try:
        cursor.execute("ALTER TABLE resumes ADD COLUMN extracted_skills TEXT DEFAULT '[]'")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()

# ---- User Operations ----
def create_user(full_name, email, hashed_password, role='Candidate'):
    conn = get_db()
    try:
        conn.execute('INSERT INTO users (full_name, email, password, role) VALUES (?, ?, ?, ?)',
                      (full_name, email, hashed_password, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_by_email(email):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user

# ---- Interview Operations ----
def create_interview(user_id, job_role, company, interview_type, total_questions):
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO interviews (user_id, job_role, company, interview_type, total_questions) VALUES (?, ?, ?, ?, ?)',
        (user_id, job_role, company, interview_type, total_questions)
    )
    interview_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return interview_id

def update_interview_results(interview_id, score, rating, feedback, strengths, weaknesses, suggestions):
    conn = get_db()
    conn.execute('''
        UPDATE interviews SET score=?, rating=?, feedback=?, strengths=?, weaknesses=?, suggestions=?
        WHERE id=?
    ''', (score, rating, feedback, json.dumps(strengths), json.dumps(weaknesses), json.dumps(suggestions), interview_id))
    conn.commit()
    conn.close()

def get_interview(interview_id):
    conn = get_db()
    interview = conn.execute('SELECT * FROM interviews WHERE id = ?', (interview_id,)).fetchone()
    conn.close()
    return interview

def get_user_interviews(user_id):
    conn = get_db()
    interviews = conn.execute(
        'SELECT * FROM interviews WHERE user_id = ? ORDER BY created_at DESC', (user_id,)
    ).fetchall()
    conn.close()
    return interviews

def get_user_interview_count(user_id):
    """Get total number of interviews taken by a user."""
    conn = get_db()
    count = conn.execute('SELECT COUNT(*) FROM interviews WHERE user_id = ?', (user_id,)).fetchone()[0]
    conn.close()
    return count

def get_user_avg_score(user_id):
    """Get average score across all interviews for a user."""
    conn = get_db()
    result = conn.execute('SELECT AVG(score) FROM interviews WHERE user_id = ? AND score > 0', (user_id,)).fetchone()
    conn.close()
    return round(result[0], 1) if result[0] else 0

# ---- Question Operations ----
def save_question(interview_id, question_number, question_text, category, difficulty):
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO questions (interview_id, question_number, question_text, category, difficulty) VALUES (?, ?, ?, ?, ?)',
        (interview_id, question_number, question_text, category, difficulty)
    )
    q_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return q_id

def update_question_answer(question_id, user_answer, ai_feedback, score):
    conn = get_db()
    conn.execute(
        'UPDATE questions SET user_answer=?, ai_feedback=?, score=? WHERE id=?',
        (user_answer, ai_feedback, score, question_id)
    )
    conn.commit()
    conn.close()

def get_interview_questions(interview_id):
    conn = get_db()
    questions = conn.execute(
        'SELECT * FROM questions WHERE interview_id = ? ORDER BY question_number', (interview_id,)
    ).fetchall()
    conn.close()
    return questions

# ---- Resume Operations ----
def save_resume(user_id, filename, extracted_text, extracted_skills=None):
    conn = get_db()
    skills_json = json.dumps(extracted_skills) if extracted_skills else '[]'
    conn.execute(
        'INSERT INTO resumes (user_id, filename, extracted_text, extracted_skills) VALUES (?, ?, ?, ?)',
        (user_id, filename, extracted_text, skills_json)
    )
    conn.commit()
    conn.close()

def get_latest_resume(user_id):
    conn = get_db()
    resume = conn.execute(
        'SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1', (user_id,)
    ).fetchone()
    conn.close()
    return resume

def get_all_resumes(user_id):
    """Get all resumes uploaded by a user."""
    conn = get_db()
    resumes = conn.execute(
        'SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC', (user_id,)
    ).fetchall()
    conn.close()
    return resumes

# ---- Performance Details Operations ----
def save_performance_details(interview_id, details):
    """Save detailed performance data for an interview."""
    conn = get_db()
    conn.execute('''
        INSERT OR REPLACE INTO performance_details
        (interview_id, technical_score, hr_score, communication_score, confidence_score,
         skill_gaps, learning_resources, improvement_roadmap, weak_question_types, strong_question_types)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        interview_id,
        details.get('technical_score', 0),
        details.get('hr_score', 0),
        details.get('communication_score', 0),
        details.get('confidence_score', 0),
        json.dumps(details.get('skill_gaps', [])),
        json.dumps(details.get('learning_resources', [])),
        json.dumps(details.get('improvement_roadmap', [])),
        json.dumps(details.get('weak_question_types', [])),
        json.dumps(details.get('strong_question_types', []))
    ))
    conn.commit()
    conn.close()

def get_performance_details(interview_id):
    """Get detailed performance data for an interview."""
    conn = get_db()
    details = conn.execute(
        'SELECT * FROM performance_details WHERE interview_id = ?', (interview_id,)
    ).fetchone()
    conn.close()
    if details:
        return {
            'technical_score': details['technical_score'],
            'hr_score': details['hr_score'],
            'communication_score': details['communication_score'],
            'confidence_score': details['confidence_score'],
            'skill_gaps': json.loads(details['skill_gaps']) if details['skill_gaps'] else [],
            'learning_resources': json.loads(details['learning_resources']) if details['learning_resources'] else [],
            'improvement_roadmap': json.loads(details['improvement_roadmap']) if details['improvement_roadmap'] else [],
            'weak_question_types': json.loads(details['weak_question_types']) if details['weak_question_types'] else [],
            'strong_question_types': json.loads(details['strong_question_types']) if details['strong_question_types'] else []
        }
    return None

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")
