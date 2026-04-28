from errno import EUSERS
from socket import gethostname
import sqlite3
import json
from time import time
from random import random
from flask import Flask, render_template, make_response, request, jsonify, url_for
import hashlib

app = Flask(__name__)

DB_PATH = "drivhus.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # create tables
    cur.execute("""CREATE TABLE IF NOT EXISTS devices (user_id INTEGER PRIMARY KEY,users VARCHAR, device_id INTEGER, status VARCHAR, is_teacher VARCHAR)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS sensors (sensor_id INTEGER PRIMARY KEY,zone_id INTEGER,sensor_type VARCHAR,is_active VARCHAR)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS sensor_readings (reading_id INTEGER PRIMARY KEY,sensor_id INTEGER,recorded_at DATE, is_active VARCHAR, unit VARCHAR)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS zones (plant_id INTEGER PRIMARY KEY, zone_id INTEGER, plant VARCHAR, plant_type VARCHAR, is_active VARCHAR, water_ammount INTEGER)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS watering_log (log_id INTEGER PRIMARY KEY, zone_id INTEGER, started_at DATE, ended_at DATE, trigger_type VARCHAR, water_litres FLOAT, status VARCHAR)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username VARCHAR UNIQUE NOT NULL, password_hash VARCHAR UNIQUE NOT NULL, role VARCHAR NOT NULL CHECK(role IN ('teacher', 'student')))""")

tables = ["devices", "sensors", "sensor_readings", "zones", "watering_log", "users"]

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
    return "HELLO WORLD"

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

@app.route('/items', methods=['POST'])
def create_items():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data received'}), 400
    # Assume data is the readings dict with table names as keys
    insert_readings(data)
    return jsonify({'status': 'Data inserted successfully'}), 201

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (
                data['username'],
                hash_password(data['password']),
                data['role']
            )
        )
        conn.commit()
        return jsonify({"status": "user created"})
    except sqlite3.IntegrityError:
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
        "SELECT id, password_hash, role FROM users WHERE username=?",
        (data['username'],)
    )
    user = cur.fetchone()

    if user and user[1] == hash_password(data['password']):
        return jsonify({
            "user_id": user[0],
            "role": user[2]
        })
    else:
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
