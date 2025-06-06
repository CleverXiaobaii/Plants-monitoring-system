from flask import Flask, jsonify
import psycopg2
from config import config

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(config.DB_URL)
    return conn

@app.route('/sensor-data')
def get_sensor_data():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM rawdata_from_sensors;")
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        data = [dict(zip(columns, row)) for row in rows]
        return jsonify(data)
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)