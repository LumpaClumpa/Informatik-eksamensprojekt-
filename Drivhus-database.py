from socket import gethostname
import sqlite3
import hashlib
from datetime import date
from flask import Flask, render_template, url_for, redirect, request, session, jsonify

app = Flask(__name__)
app.secret_key = "key"

DB_PATH = "drivhus.db"
TABLES = ["devices", "sensors", "sensor_readings", "zones", "watering_log", "users", "plant_tasks"]



# DATABASE SETUP


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS devices (
        user_id    INTEGER PRIMARY KEY,
        users      VARCHAR,
        device_id  INTEGER,
        status     VARCHAR,
        is_teacher VARCHAR
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS sensors (
        sensor_id   INTEGER PRIMARY KEY,
        zone_id     INTEGER,
        sensor_type VARCHAR,
        is_active   VARCHAR
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS sensor_readings (
        reading_id  INTEGER PRIMARY KEY,
        sensor_id   INTEGER,
        recorded_at DATE,
        is_active   VARCHAR,
        unit        VARCHAR
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS zones (
        plant_id      INTEGER PRIMARY KEY,
        zone_id       INTEGER,
        plant         VARCHAR,
        plant_type    VARCHAR,
        is_active     VARCHAR,
        water_ammount INTEGER
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS watering_log (
        log_id       INTEGER PRIMARY KEY,
        zone_id      INTEGER,
        started_at   DATE,
        ended_at     DATE,
        trigger_type VARCHAR,
        water_litres FLOAT,
        status       VARCHAR
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id               INTEGER PRIMARY KEY,
        username         VARCHAR UNIQUE NOT NULL,
        password_hash    VARCHAR NOT NULL,
        teacher_password VARCHAR,
        role             VARCHAR NOT NULL CHECK(role IN ('teacher', 'student'))
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS plant_tasks (
        task_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        plant_id     INTEGER NOT NULL,
        task_text    VARCHAR NOT NULL,
        is_complete  INTEGER DEFAULT 0,
        completed_by VARCHAR,
        completed_at DATE
    )""")

    conn.commit()
    conn.close()



# HELPERS

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def insert_readings(readings_dict):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for table, rows in readings_dict.items():
        if table in TABLES:
            for row in rows:
                columns = ', '.join(row.keys())
                placeholders = ', '.join('?' * len(row))
                values = tuple(row.values())
                cur.execute(
                    f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})",
                    values
                )
    conn.commit()
    conn.close()


# ROUTES — GENERELLE SIDER

@app.route('/')
def home():
    locked = not session.get("logged_in")
    return render_template("home.html", locked=locked)

@app.route('/plants')
def plants_overview():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT plant_id, zone_id, plant, plant_type, is_active, water_ammount
        FROM zones ORDER BY zone_id, plant
    """)
    plants = cur.fetchall()
    conn.close()
    return render_template("plants.html", plants=plants)


# ROUTES — AUTH

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, password_hash, role FROM users WHERE LOWER(username) = ?",
            (username,)
        )
        user = cur.fetchone()
        conn.close()

        if user and user["password_hash"] == hash_password(password):
            session["logged_in"] = True
            session["user_id"]   = user["id"]
            session["username"]  = user["username"]
            session["role"]      = user["role"]

            if user["role"] == "teacher":
                return redirect(url_for("velkommen_laerer"))
            else:
                return redirect(url_for("velkommen_elev"))

        return render_template("login.html", error="Ikke gyldigt brugernavn eller kodeord")

    return render_template("login.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route('/register', methods=['GET'])
def show_register():
    return render_template("register.html")


@app.route('/register', methods=['POST'])
def register():
    data = request.form

    username = data.get('username')
    password = data.get('password')
    role     = data.get('role')

    if not username or not password or not role:
        return jsonify({"error": "Mangler brugernavn, kodeord eller rolle"}), 400

    conn = get_db()
    cur = conn.cursor()
    try:
        teacher_pwd = data.get('teacher_password')
        teacher_pwd_hash = hash_password(teacher_pwd) if teacher_pwd else None
        cur.execute(
            "INSERT INTO users (username, password_hash, teacher_password, role) VALUES (?, ?, ?, ?)",
            (username, hash_password(password), teacher_pwd_hash, role)
        )
        conn.commit()
        return redirect(url_for("login"))
    except sqlite3.IntegrityError:
        return jsonify({"error": "Brugernavnet findes allerede"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# ROUTES — ROLLE SIDER

@app.route('/velkommen-laerer')
def velkommen_laerer():
    if session.get("role") != "teacher":
        return redirect(url_for("home"))
    return render_template("lærer.html")


@app.route('/velkommen-elev')
def velkommen_elev():
    if session.get("role") != "student":
        return redirect(url_for("home"))
    return render_template("elev.html")


# ROUTES — OPGAVER

@app.route('/opgaver')
def opgaver():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT pt.task_id, pt.task_text, pt.is_complete, pt.completed_by, pt.completed_at,
               z.plant, z.plant_type, z.zone_id, z.plant_id
        FROM plant_tasks pt
        JOIN zones z ON pt.plant_id = z.plant_id
        ORDER BY pt.is_complete ASC, pt.task_id ASC
    """)
    tasks = cur.fetchall()

    cur.execute("SELECT plant_id, zone_id, plant, plant_type FROM zones WHERE is_active = 'yes'")
    plants = cur.fetchall()
    conn.close()

    return render_template("opgave.html",
                           tasks=tasks,
                           plants=plants,
                           username=session.get("username"),
                           role=session.get("role"))


@app.route('/opgaver/add', methods=['POST'])
def add_task():
    if session.get("role") != "teacher":
        return jsonify({"error": "Kun lærere kan tilføje opgaver"}), 403

    plant_id  = request.form.get("plant_id")
    task_text = request.form.get("task_text")

    if not plant_id or not task_text:
        return jsonify({"error": "Mangler plante eller opgavetekst"}), 400

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO plant_tasks (plant_id, task_text) VALUES (?, ?)", (plant_id, task_text))
        conn.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    return redirect(url_for("opgaver"))


@app.route('/opgaver/complete/<int:task_id>', methods=['POST'])
def complete_task(task_id):
    if session.get("role") != "student":
        return jsonify({"error": "Kun elever kan fuldføre opgaver"}), 403

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE plant_tasks
            SET is_complete = 1, completed_by = ?, completed_at = ?
            WHERE task_id = ?
        """, (session.get("username"), date.today().isoformat(), task_id))
        conn.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    return redirect(url_for("opgaver"))


# ROUTES — API

@app.route('/items', methods=['GET'])
def get_items():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        data = {}
        for table in TABLES:
            cur.execute(f"SELECT * FROM {table}")
            rows = cur.fetchall()
            columns = [col[0] for col in cur.description]
            data[table] = [dict(zip(columns, row)) for row in rows]
        conn.close()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/items', methods=['POST'])
def create_items():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data received'}), 400
    insert_readings(data)
    return jsonify({'status': 'Data inserted successfully'}), 201


# EKSEMPELDATA & START

EXAMPLE_DATA = {
    "devices": [
        {"user_id": 1, "users": "Alice", "device_id": 101, "status": "online",  "is_teacher": "TRUE"},
        {"user_id": 2, "users": "Bob",   "device_id": 102, "status": "offline", "is_teacher": "FALSE"},
    ],
    "sensors": [
        {"sensor_id": 1, "zone_id": 1, "sensor_type": "temperature", "is_active": "yes"},
        {"sensor_id": 2, "zone_id": 1, "sensor_type": "humidity",    "is_active": "yes"},
    ],
}

if __name__ == '__main__':
    init_db()
    insert_readings(EXAMPLE_DATA)
    if 'liveconsole' not in gethostname():
        app.run(debug=True)