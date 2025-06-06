import os
import paho.mqtt.client as mqtt
import pymysql
import json
import time
import logging
from dotenv import load_dotenv

# MQTT配置
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
TOPIC = "greenhouse/#"
CLIENT_ID = "mqtt-listener"

# MySQL配置
#DB_HOST = "localhost"
#DB_USER = "root"
#DB_PASS = "password"
#DB_NAME = "sensor_db"
load_dotenv()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(TOPIC)
    else:
        print(f"Connection failed with code {rc}")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        id=payload.get("id")
        sensor_id=payload.get("sensor_id")
        plant_id=payload.get("plant_id")
        sensor_name=payload.get("sensor_name")
        time_stamp=payload.get("time_stamp")
        temperature=payload.get("temperature")
        humidity=payload.get("humidity")
        soil_moisture=payload.get("soil_moisture")
        is_anomaly=payload.get("is_anomaly")
        save_to_db(id,sensor_id,plant_id,sensor_name,time_stamp,temperature,humidity,soil_moisture,is_anomaly)
    except Exception as e:
        logging.error(f"Message processing failed: {e}")


def save_to_db(id,sensor_id,plant_id,sensor_name,time_stamp,temperature,humidity,soil_moisture,is_anomaly):
    try:
        db = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
        cursor = db.cursor()
        sql = """
            INSERT INTO rawdata_from_sensors (id, sensor_id, plant_id, sensor_name, time_stamp, temperature, humidity, soil_moisture, is_anomaly)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (id,sensor_id,plant_id,sensor_name,time_stamp,temperature,humidity,soil_moisture,is_anomaly))
        db.commit()
        print(f"Inserted: {id}")
    except pymysql.Error as e:
        logging.error(f"DB error: {e}")
        db.rollback()
    finally:
        if db: db.close()


# 自动重连机制（指数退避策略）
def on_disconnect(client, userdata, rc):
    logging.warning(f"Disconnected. Attempting reconnect...")
    reconnect_delay = 1
    while True:
        try:
            client.reconnect()
            return
        except:
            time.sleep(min(reconnect_delay, 60))
            reconnect_delay *= 2

    # 初始化MQTT客户端
def listening():
    client = mqtt.Client(client_id=CLIENT_ID, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_forever()

if __name__ == "__main__":
    listening()
