import psycopg2

def calc_avg(cur):
    cur.execute("""
        SELECT sensor_id, AVG(temperature) AS avg_temp, AVG(humidity) AS avg_humidity, AVG(soil_moisture) AS avg_soil_moisture
        FROM rawdata_from_sensors
        GROUP BY sensor_id
        ORDER BY sensor_id;
    """)
    results = cur.fetchall()
    for row in results:
        sensor_id, avg_temp, avg_humidity, avg_soil_moisture = row
        print(f"Sensor: {sensor_id}, Avg Temperature: {avg_temp:.2f}, Avg Humidity: {avg_humidity:.2f}, Avg Soil Moisture: {avg_soil_moisture:.2f}")
# This script calculates the average temperature, humidity and soil moisture from sensor data in entire duration.

def calc_avg_day_sensor(cur, date, sensor_id):
    cur.execute("""
        SELECT AVG(temperature) AS avg_temp, AVG(humidity) AS avg_humidity, AVG(soil_moisture) AS avg_soil_moisture
        FROM rawdata_from_sensors
        WHERE DATE(time_stamp) = %s AND sensor_id = %s;
    """, (date, sensor_id))
    result = cur.fetchone()
    if result and all(val is not None for val in result):
        avg_temp, avg_humidity, avg_soil_moisture = result
        print(f"Date: {date}, Sensor: {sensor_id} | Avg Temperature: {avg_temp:.2f}, Avg Humidity: {avg_humidity:.2f}, Avg Soil Moisture: {avg_soil_moisture:.2f}")
    else:
        print(f"No data found for (Date: {date}, Sensor: {sensor_id})")
# This script calculates the average temperature, humidity and soil moisture for a specific sensor on a specific date.

def fetch_sensor_data(cur):
    cur.execute("SELECT * FROM rawdata_from_sensors;")
    return cur.fetchall()

def main():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="plant_monitor",
        user="chikara"
        # password="postgres"
    )
    cur = conn.cursor()
    try:
        calc_avg(cur)
        calc_avg_day_sensor(cur, '2025-06-01', 1)  # Example date and sensor_id
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()