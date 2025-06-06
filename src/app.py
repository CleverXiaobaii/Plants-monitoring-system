# app.py
from flask import Flask, jsonify, request, render_template
import psycopg2
from calc import (
    get_db_connection,
    fetch_sensor_data
)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('test.html')

@app.route('/sensor-data', methods=['GET']) # return all sensor data
def sensor_data(): 
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        data = fetch_sensor_data(cur)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()
        
    return jsonify(data)

@app.route('/latest/<int:sensor_id>', methods=['GET']) # return latest data by sensor id
def latest_data(sensor_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT *
            FROM rawdata_from_sensors
            WHERE sensor_id = %s
            ORDER BY time_stamp DESC
            LIMIT 1;
        """, (sensor_id,))
        row = cur.fetchone()
        if row is None:
            return jsonify({"error": "No data found"}), 404
        sensor_data = {
            "sensor_id": row[1],
            "time_stamp": row[2],
            "temperature": row[3],
            "humidity": row[4],
            "soil_moisture": row[5],
            "is_anomaly": row[6]
        }
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

    return jsonify(sensor_data)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)