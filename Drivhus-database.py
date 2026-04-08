from socket import gethostname
import sqlite3
import json
from time import time
from random import random
from flask import Flask, render_template, make_response, request, jsonify, url_for

app = Flask(__name__)

DB_PATH = "drivhus.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # create tables
    cur.execute("""CREATE TABLE IF NOT EXISTS devices (user_id INTEGER PRIMARY KEY,users VARCHAR, device_id INTEGER, status VARCHAR)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS sensors (sensor_id INTEGER PRIMARY KEY,zone_id INTEGER,sensor_type VARCHAR,is_active VARCHAR)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS sensor_readings (reading_id INTEGER PRIMARY KEY,sensor_id INTEGER,recorded_at DATE, is_active VARCHAR, unit VARCHAR)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS zones (plant_id INTEGER PRIMARY KEY, zone_id INTEGER, plant VARCHAR, plant_type VARCHAR, is_active VARCHAR, water_ammount INTEGER)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS watering_log (log_id INTEGER PRIMARY KEY, zone_id INTEGER, started_at DATE, ended_at, DATE, trigger_type VARCHAR, water_litres FLOAT, status VARCHAR)""")

def insertValueInTableColumn(value, table, column):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    columnb="efefe"
    lokalenr=444
    decibel=44
    cur.execute("SELECT COUNT(*) FROM devices")
    if cur.fetchone()[0] == 0:
        cur.execute(f"INSERT INTO {table} ({column}, {columnb}) VALUES ({lokalenr}, {value})")
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return "HELLO WORLD"

@app.route('/items', methods=['POST'])
def create_item():
    data = request.get_json()

    # Validate input
    if not data or 'name' not in data:
        return jsonify({'error': 'Missing "name" in request data'}), 400

    name = data['name']



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

    tables = ["devices", "sensors", "sensor_readings", "zones", "watering_log"]

    for table in tables:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        data[table] = [dict(zip(columns, row)) for row in rows]

    conn.close()
    return jsonify(data)


if __name__ == '__main__':
    init_db()
    if 'liveconsole' not in gethostname():
        app.run()