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



if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)