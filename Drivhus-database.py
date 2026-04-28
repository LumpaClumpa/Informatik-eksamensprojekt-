from errno import EUSERS
from socket import gethostname
import sqlite3
import json
from time import time
from random import random
from flask import Flask, render_template, make_response, request, jsonify, url_for
import hashlib
from flask import session, redirect

app = Flask(__name__)
app.secret_key = "key"

DB_PATH = "drivhus.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS devices (user_id INTEGER PRIMARY KEY,users VARCHAR, device_id INTEGER, status VARCHAR, is_teacher VARCHAR)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS sensors (sensor_id INTEGER PRIMARY KEY,zone_id INTEGER,sensor_type VARCHAR,is_active VARCHAR)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS sensor_readings (reading_id INTEGER PRIMARY KEY,sensor_id INTEGER,recorded_at DATE, is_active VARCHAR, unit VARCHAR)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS zones (plant_id INTEGER PRIMARY KEY, zone_id INTEGER, plant VARCHAR, plant_type VARCHAR, is_active VARCHAR, water_ammount INTEGER)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS watering_log (log_id INTEGER PRIMARY KEY, zone_id INTEGER, started_at DATE, ended_at DATE, trigger_type VARCHAR, water_litres FLOAT, status VARCHAR)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username VARCHAR UNIQUE NOT NULL, password_hash VARCHAR NOT NULL, teacher_password VARCHAR, role VARCHAR NOT NULL CHECK(role IN ('teacher', 'student')))""")
    cur.execute("""CREATE TABLE IF NOT EXISTS plant_tasks (task_id INTEGER PRIMARY KEY AUTOINCREMENT,plant_id INTEGER NOT NULL,task_text VARCHAR NOT NULL,is_complete INTEGER DEFAULT 0,completed_by VARCHAR,completed_at DATE)""")

tables = ["devices", "sensors", "sensor_readings", "zones", "watering_log", "users", "plant_tasks"]

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def insert_readings(readings_dict):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for table, rows in readings_dict.items():
        if table in tables:  # Only insert into existing tables
            for row in rows:
                columns = ', '.join(row.keys())
                placeholders = ', '.join('?' * len(row))
                values = tuple(row.values())
                cur.execute(f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})", values)
    conn.commit()
    conn.close()



@app.route('/')
def home():
    return render_template("home.html")

'''@app.route('/items', methods=['POST'])
def create_item():
    data = request.get_json()

    # Validate input
    if not data or 'name' not in data:
        return jsonify({'error': 'Missing "name" in request data'}), 400

    name = data['name']'''



''''@app.route("/arduino", methods=["POST"])
def receive_from_arduino():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON received"}), 400
    # expected JSON: { "lokale": 2221, "db": 55.2 }
    try:
        lokale = int(data.get("lokale"))
        db_val = float(data.get("db"))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid payload, expected 'lokale' and 'db'"}), 400
    ts = int(time() * 1000)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO maalinger (ts, lokale, db) VALUES (?, ?, ?)", (ts, lokale, db_val))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "lokale": lokale, "db": db_val, "ts": ts}), 201
'''


# Define the GET /items endpoint
@app.route('/items', methods=['GET'])
def get_items():
    conn = sqlite3.connect('drivhus.db')
    cursor = conn.cursor()

    data = {}

    # Create list of all tables in database

    for table in tables: # For each table fetch data, for each row create a dict with column names as keys and values as values, add to data dict with table name as key
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall() # Fetch all rows from the current table
        columns = [col[0] for col in cursor.description] # Get column names from cursor description
        data[table] = [dict(zip(columns, row)) for row in rows]

    conn.close()
    return jsonify(data)

@app.route('/plants')
def plants_overview():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT plant_id, zone_id, plant, plant_type, is_active, water_ammount
        FROM zones
        ORDER BY zone_id, plant
    """)

    plants = cur.fetchall()
    conn.close()

    return render_template("plants.html", plants=plants)

@app.route('/items', methods=['POST'])
def create_items():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data received'}), 400
    # Assume data is the readings dict with table names as keys
    insert_readings(data)
    return jsonify({'status': 'Data inserted successfully'}), 201

@app.route('/opgaver')
def opgaver():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            plant_tasks.task_id,
            plant_tasks.task_text,
            plant_tasks.is_complete,
            plant_tasks.completed_by,
            plant_tasks.completed_at,
            zones.plant,
            zones.plant_type,
            zones.zone_id,
            zones.plant_id
        FROM plant_tasks
        JOIN zones ON plant_tasks.plant_id = zones.plant_id
        ORDER BY plant_tasks.is_complete, zones.plant
    """)

    tasks = cur.fetchall()

    cur.execute("""
        SELECT plant_id, plant, plant_type, zone_id
        FROM zones
        WHERE is_active = 'yes' OR is_active = 'TRUE' OR is_active = 'true'
        ORDER BY plant
    """)
    plants = cur.fetchall()

    conn.close()

    return render_template(
        "opgaver.html",
        tasks=tasks,
        plants=plants,
        role=session.get("role"),
        username=session.get("username")
    )


@app.route('/opgaver/complete/<int:task_id>', methods=['POST'])
def complete_task(task_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        UPDATE plant_tasks
        SET is_complete = 1,
            completed_by = ?,
            completed_at = datetime('now')
        WHERE task_id = ?
    """, (session.get("username", "student"), task_id))

    conn.commit()
    conn.close()

    return redirect('/opgaver')


@app.route('/opgaver/add', methods=['POST'])
def add_task():
    if session.get("role") != "teacher":
        return jsonify({"error": "Only teachers can add tasks"}), 403

    plant_id = request.form.get("plant_id")
    task_text = request.form.get("task_text")

    if not plant_id or not task_text:
        return jsonify({"error": "Missing plant or task text"}), 400

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO plant_tasks (plant_id, task_text)
        VALUES (?, ?)
    """, (plant_id, task_text))

    conn.commit()
    conn.close()

    return redirect('/opgaver')


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        teacher_pwd = data.get('teacher_password')
        teacher_pwd_hash = hash_password(teacher_pwd) if teacher_pwd else None

        cur.execute(
            "INSERT INTO users (username, password_hash, teacher_password, role) VALUES (?, ?, ?, ?)",
            (
                data['username'],
                hash_password(data['password']),
                teacher_pwd_hash,
                data['role']
            )
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "user created"}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "username already exists"}), 400


@app.route('/register', methods=['GET'])
def show_register():
    return render_template("register.html")


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        "SELECT id, password_hash, teacher_password, role FROM users WHERE username=?",
        (data['username'],)
    )
    user = cur.fetchone()
    conn.close()

    if user:
        password_hash = user[1]
        teacher_password_hash = user[2]

        # Check if it's a student login
        if password_hash == hash_password(data.get('password', '')):
            session["user_id"] = user[0]
            session["username"] = data["username"]
            session["role"] = "student"
            return jsonify({"user_id": user[0], "role": "student"}), 200

        elif teacher_password_hash and teacher_password_hash == hash_password(data.get('teacher_password', '')):
            session["user_id"] = user[0]
            session["username"] = data["username"]
            session["role"] = "teacher"
            return jsonify({"user_id": user[0], "role": "teacher"}), 200

    return jsonify({"error": "invalid login"}), 401


@app.route('/login', methods=['GET'])
def show_login():
    return render_template("login.html")

readings = { # example data structure for readings
    "devices": [
        {"user_id": 1, "users": "Alice", "device_id": 101, "status": "online", "is_teacher": "TRUE"},
        {"user_id": 2, "users": "Bob", "device_id": 102, "status": "offline", "is_teacher": "FALSE"},
    ],
    "sensors": [
        {"sensor_id": 1, "zone_id": 1, "sensor_type": "temperature", "is_active": "yes"},
        {"sensor_id": 2, "zone_id": 1, "sensor_type": "humidity", "is_active": "yes"}
    ],
}
#serialize the data dictionary to a JSON string
json_data = json.dumps(readings)

if __name__ == '__main__':
    init_db()
    # Insert the example data by loading from the JSON string
    insert_readings(json.loads(json_data))
    if 'liveconsole' not in gethostname():
        app.run()
