import psycopg2

def calc_avg(cur):
    cur.execute("""
        SELECT sensor_id, AVG(temperature) AS avg_temp, AVG(humidity) AS avg_humidity, AVG(soil_moisture) AS avg_soil_moisture
        FROM rawdata_from_sensors
        GROUP BY sensor_id;
    """)
    results = cur.fetchall()
    for row in results:
        sensor_id, avg_temp, avg_humidity, avg_soil_moisture = row
        print(f"Sensor: {sensor_id}, Avg Temperature: {avg_temp:.2f}, Avg Humidity: {avg_humidity:.2f}, Avg Soil Moisture: {avg_soil_moisture:.2f}")
# This script calculates the average temperature, humidity and soil moisture from sensor data.

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
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()