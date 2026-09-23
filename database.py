import sqlite3
import os
from datetime import datetime

# Render'da /data diskka, lokalda esa joriy papkaga
DB_NAME = os.environ.get("DB_PATH", "school_bot.db")

# Papka mavjud bo'lmasa yaratish
_db_dir = os.path.dirname(DB_NAME)
if _db_dir and not os.path.exists(_db_dir):
    os.makedirs(_db_dir, exist_ok=True)

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    # Users jadvali
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            class_id INTEGER,
            registered_at TEXT
        )
    """)
    # Classes jadvali
    cur.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)
    # Subjects jadvali
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER,
            name TEXT,
            FOREIGN KEY (class_id) REFERENCES classes(id)
        )
    """)
    # Tests jadvali
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER,
            name TEXT,
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        )
    """)
    # Questions jadvali
    cur.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER,
            question_text TEXT,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            correct_answer TEXT,
            type TEXT,
            image_file_id TEXT,
            FOREIGN KEY (test_id) REFERENCES tests(id)
        )
    """)
    # Results jadvali
    cur.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            test_id INTEGER,
            score INTEGER,
            total_questions INTEGER,
            percentage REAL,
            completed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (test_id) REFERENCES tests(id)
        )
    """)
    # Standart sinflarni qo'shish
    for i in range(5, 12):
        cur.execute("INSERT OR IGNORE INTO classes (name) VALUES (?)", (f"{i}-sinf",))

    # === YANGI: Migratsiya ===
    try:
        cur.execute("ALTER TABLE questions ADD COLUMN image_file_id TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

def add_user(user_id, full_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO users (user_id, full_name, registered_at) VALUES (?, ?, ?)",
                (user_id, full_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def update_user_class(user_id, class_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET class_id = ? WHERE user_id = ?", (class_id, user_id))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return user

def get_classes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM classes ORDER BY id")
    classes = cur.fetchall()
    conn.close()
    return classes

def add_subject(class_id, name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO subjects (class_id, name) VALUES (?, ?)", (class_id, name))
    conn.commit()
    conn.close()

def get_subjects_by_class(class_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM subjects WHERE class_id = ?", (class_id,))
    subjects = cur.fetchall()
    conn.close()
    return subjects

def add_test(subject_id, name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO tests (subject_id, name) VALUES (?, ?)", (subject_id, name))
    test_id = cur.lastrowid
    conn.commit()
    conn.close()
    return test_id

def get_tests_by_subject(subject_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tests WHERE subject_id = ?", (subject_id,))
    tests = cur.fetchall()
    conn.close()
    return tests

def get_all_tests():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.id, t.name, s.name as subject_name, c.name as class_name
        FROM tests t
        JOIN subjects s ON t.subject_id = s.id
        JOIN classes c ON s.class_id = c.id
    """)
    tests = cur.fetchall()
    conn.close()
    return tests

def delete_test(test_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM questions WHERE test_id = ?", (test_id,))
    cur.execute("DELETE FROM results WHERE test_id = ?", (test_id,))
    cur.execute("DELETE FROM tests WHERE id = ?", (test_id,))
    conn.commit()
    conn.close()

def add_question(test_id, question_text, option_a, option_b, option_c, option_d,
                 correct_answer, q_type, image_file_id=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO questions (test_id, question_text, option_a, option_b, option_c, option_d,
                               correct_answer, type, image_file_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (test_id, question_text, option_a, option_b, option_c, option_d,
          correct_answer, q_type, image_file_id))
    conn.commit()
    conn.close()

def get_questions_by_test(test_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM questions WHERE test_id = ?", (test_id,))
    questions = cur.fetchall()
    conn.close()
    return questions

def save_result(user_id, test_id, score, total, percentage):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO results (user_id, test_id, score, total_questions, percentage, completed_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, test_id, score, total, percentage, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user_results(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.*, t.name as test_name, s.name as subject_name
        FROM results r
        JOIN tests t ON r.test_id = t.id
        JOIN subjects s ON t.subject_id = s.id
        WHERE r.user_id = ?
        ORDER BY r.completed_at DESC
    """, (user_id,))
    results = cur.fetchall()
    conn.close()
    return results

def get_rating_by_class(class_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.user_id, u.full_name,
               COUNT(r.id) as tests_taken,
               COALESCE(AVG(r.percentage), 0) as avg_percentage,
               COALESCE(SUM(r.score), 0) as total_score
        FROM users u
        LEFT JOIN results r ON u.user_id = r.user_id
        WHERE u.class_id = ?
        GROUP BY u.user_id
        ORDER BY avg_percentage DESC, total_score DESC
    """, (class_id,))
    rating = cur.fetchall()
    conn.close()
    return rating

def get_test_best_results(test_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.user_id, u.full_name,
               COALESCE(MAX(r.percentage), 0) as best_percentage,
               COALESCE(MAX(r.score), 0) as best_score,
               r.total_questions,
               r.completed_at
        FROM results r
        JOIN users u ON r.user_id = u.user_id
        WHERE r.test_id = ?
        GROUP BY r.user_id
        ORDER BY best_percentage DESC, best_score DESC
    """, (test_id,))
    results = cur.fetchall()
    conn.close()
    return results


# ================= REYTING (TUZATILGAN) =================

def get_rating_by_subject(subject_id):
    """
    Fan bo'yicha reyting.
    MUHIM: Faqat shu fanga tegishli testlar hisobga olinadi.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Avval fanning class_id sini olamiz
    cur.execute("SELECT class_id FROM subjects WHERE id = ?", (subject_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return []
    class_id = row['class_id']

    # Faqat shu fanga tegishli test natijalari hisobga olinadi
    cur.execute("""
        SELECT u.user_id, u.full_name,
               COUNT(r.id) as tests_taken,
               COALESCE(AVG(r.percentage), 0) as avg_percentage,
               COALESCE(SUM(r.score), 0) as total_score
        FROM users u
        LEFT JOIN results r ON u.user_id = r.user_id
        LEFT JOIN tests t ON r.test_id = t.id
        WHERE u.class_id = ?
          AND (r.id IS NULL OR t.subject_id = ?)
        GROUP BY u.user_id
        ORDER BY avg_percentage DESC, total_score DESC
    """, (class_id, subject_id))

    rating = cur.fetchall()
    conn.close()
    return rating


# ================= SAVOLLARNI TAHRIRLASH =================

def get_question(question_id):
    """ID bo'yicha bitta savolni olish. Dict qaytaradi."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
    question = cur.fetchone()
    conn.close()
    if question is None:
        return None
    return dict(question)


def update_question(question_id, **kwargs):
    allowed_fields = {
        'question_text',
        'option_a',
        'option_b',
        'option_c',
        'option_d',
        'correct_answer',
        'type',
        'image_file_id'
    }
    fields_to_update = {k: v for k, v in kwargs.items() if k in allowed_fields}
    if not fields_to_update:
        return False
    set_clause = ", ".join([f"{k} = ?" for k in fields_to_update.keys()])
    values = list(fields_to_update.values()) + [question_id]
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"UPDATE questions SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def delete_question(question_id):
    """Bitta savolni o'chirish."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_question_by_num_in_test(test_id, num):
    """Testdagi N-savolni olish (1-dan boshlab)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM questions
        WHERE test_id = ?
        ORDER BY id
        LIMIT 1 OFFSET ?
    """, (test_id, num - 1))
    question = cur.fetchone()
    conn.close()
    if question is None:
        return None
    return dict(question)


def count_questions_in_test(test_id):
    """Testdagi savollar sonini qaytaradi."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM questions WHERE test_id = ?", (test_id,))
    row = cur.fetchone()
    conn.close()
    return row['cnt'] if row else 0


# ================= REYTINGNI TOZALASH (YANGI) =================

def delete_results_by_subject(subject_id):
    """
    Fan bo'yicha BARCHA natijalarni o'chirish.
    (Fan ostidagi barcha testlarning natijalari o'chiriladi)
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM results
            WHERE test_id IN (SELECT id FROM tests WHERE subject_id = ?)
        """, (subject_id,))
        conn.commit()
        return cur.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def delete_results_by_test(test_id):
    """Bitta test bo'yicha barcha natijalarni o'chirish."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM results WHERE test_id = ?", (test_id,))
        conn.commit()
        return cur.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def delete_results_by_user_and_subject(user_id, subject_id):
    """Bitta o'quvchining fan bo'yicha natijalarini o'chirish."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM results
            WHERE user_id = ?
              AND test_id IN (SELECT id FROM tests WHERE subject_id = ?)
        """, (user_id, subject_id))
        conn.commit()
        return cur.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def count_results_by_subject(subject_id):
    """Fan bo'yicha jami natijalar sonini qaytaradi."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as cnt FROM results
        WHERE test_id IN (SELECT id FROM tests WHERE subject_id = ?)
    """, (subject_id,))
    row = cur.fetchone()
    conn.close()
    return row['cnt'] if row else 0


def set_question_image(question_id, file_id):
    """Savolga rasm biriktirish (file_id orqali)."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE questions SET image_file_id = ? WHERE id = ?", (file_id, question_id))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def remove_question_image(question_id):
    """Savoldan rasmni o'chirish."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE questions SET image_file_id = NULL WHERE id = ?", (question_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
