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

def calc_min_max_day_sensor(cur, date, sensor_id):
    cur.execute("""
        SELECT MIN(temperature) AS min_temp, MAX(temperature) AS max_temp,
               MIN(humidity) AS min_humidity, MAX(humidity) AS max_humidity,
               MIN(soil_moisture) AS min_soil_moisture, MAX(soil_moisture) AS max_soil_moisture
        FROM rawdata_from_sensors
        WHERE DATE(time_stamp) = %s AND sensor_id = %s;
    """, (date, sensor_id))
    result = cur.fetchone()
    if result and all(val is not None for val in result):
        min_temp, max_temp, min_humidity, max_humidity, min_soil_moisture, max_soil_moisture = result
        print(f"Date: {date}, Sensor: {sensor_id} | Min Temp: {min_temp:.2f}, Max Temp: {max_temp:.2f}, "
              f"Min Humidity: {min_humidity:.2f}, Max Humidity: {max_humidity:.2f}, "
              f"Min Soil Moisture: {min_soil_moisture:.2f}, Max Soil Moisture: {max_soil_moisture:.2f}")
    else:
        print(f"No data found for (Date: {date}, Sensor: {sensor_id})")
# This script calculates the minimum and maximum temperature, humidity and soil moisture for a specific sensor on a specific date.

def stats(cur, date, sensor_id):
    cur.execute("""
        SELECT COUNT(*), AVG(temperature) AS avg_temp, AVG(humidity) AS avg_humidity, AVG(soil_moisture) AS avg_soil_moisture,
            MIN(temperature) AS min_temp, MIN(humidity) AS min_humidity, MIN(soil_moisture) AS min_soil_moisture,
            MAX(temperature) AS max_temp, MAX(humidity) AS max_humidity, MAX(soil_moisture) AS max_soil_moisture,
            STDDEV(temperature) AS std_temp, STDDEV(humidity) AS std_humidity, STDDEV(soil_moisture) AS std_soil_moisture
        FROM rawdata_from_sensors
        WHERE DATE(time_stamp) = %s AND sensor_id = %s;
    """, (date, sensor_id))
    result = cur.fetchone()
    if result and all(val is not None for val in result):
        count, avg_temp, avg_humidity, avg_soil_moisture, min_temp, min_humidity, min_soil_moisture, \
        max_temp, max_humidity, max_soil_moisture, std_temp, std_humidity, std_soil_moisture = result
        print(f"Date: {date}, Sensor: {sensor_id} \n Count: {count} \n Temp) Avg: {avg_temp:.2f}, Min: {min_temp:.2f}, Max: {max_temp:.2f}, StdDev: {std_temp:.2f} \n Humidity) Avg: {avg_humidity:.2f}, Min: {min_humidity:.2f}, Max: {max_humidity:.2f}, StdDev: {std_humidity:.2f} \n Soil Moisture) Avg: {avg_soil_moisture:.2f}, Min: {min_soil_moisture:.2f}, Max: {max_soil_moisture:.2f}, StdDev: {std_soil_moisture:.2f}")
    else:
        print(f"No data found for (Date: {date}, Sensor: {sensor_id})")

def fetch_sensor_data(cur):
    cur.execute("SELECT * FROM rawdata_from_sensors;")
    return cur.fetchall()

def main():
    conn = psycopg2.connect(
        host="innovatinsa.piwio.fr",
        port=5432,
        dbname="plant_monitor",
        user="postgres",
        password="innovatinsa-piwio-5432"
    )
    cur = conn.cursor()
    try:
        calc_avg(cur)
        print("---")
        # calc_avg_day_sensor(cur, '2025-06-05', 1)
        # calc_min_max_day_sensor(cur, '2025-06-05', 1)
        stats(cur, '2025-06-05', 1)
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()