# app.py
from flask import Flask, jsonify, request, render_template
import psycopg2
from config import config

def get_db_connection():
    return psycopg2.connect(config.DB_URL)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('test.html')

@app.route('/sensor-data', methods=['GET']) # return all sensor data
def sensor_data(): 
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM rawdata_from_sensors;")
        data = cur.fetchall()
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

@app.route('/summary', methods=['GET']) # return average temperature
def avg_temp():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            WITH latest_per_sensor AS (
                SELECT DISTINCT ON (sensor_id) *
                FROM rawdata_from_sensors
                ORDER BY sensor_id, time_stamp DESC
            )
            SELECT
                AVG(temperature) AS avg_temp,
                AVG(humidity) AS avg_humidity,
                AVG(soil_moisture) AS avg_soil_moisture,
                SUM(CASE WHEN is_anomaly THEN 1 ELSE 0 END) AS anomaly_count
            FROM latest_per_sensor;
        """)
        row = cur.fetchone()
        if row is None or all(val is None for val in row):
            return jsonify({"error": "Data unavailable"}), 404
        result = {
            "avg_temp": row[0],
            "avg_humidity": row[1],
            "avg_soil_moisture": row[2],
            "anomaly_count": row[3]
        }
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

    return jsonify(result)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)