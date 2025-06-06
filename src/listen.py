import os
import paho.mqtt.client as mqtt
import psycopg2
import json
import time
import logging
from dotenv import load_dotenv

# MQTT配置
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
TOPIC = "greenhouse/#"
CLIENT_ID = "mqtt-listener"

# MySQL配置 - 确保这些变量正确设置
DB_HOST = "innovatinsa.piwio.fr"
DB_PORT = 5432
DB_NAME = "group02"  # 这里需要填写实际的数据库名称
DB_USER = "postgres"
DB_PASSWORD = "innovatinsa-piwio-5432"
load_dotenv()  # 确保.env文件中有正确的值


def on_connect(client, userdata, flags, reason_code, properties):
    """修复：添加了 reason_code 和 properties 参数"""
    if reason_code == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(TOPIC)
    else:
        print(f"Connection failed with code {reason_code}")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        #id = payload.get("id")
        sensor_id = payload.get("sensor_id")
        #plant_id = payload.get("plant_id")
        #sensor_name = payload.get("sensor_name")
        time_stamp = payload.get("timestamp")
        temperature = payload.get("temperature")
        humidity = payload.get("humidity")
        soil_moisture = payload.get("soil_moisture")
        is_anomaly = payload.get("is_anomaly")

        save_to_db(sensor_id, time_stamp,
                   temperature, humidity, soil_moisture, is_anomaly)
    except Exception as e:
        logging.error(f"消息处理失败: {e}")


def save_to_db(sensor_id, time_stamp,
               temperature, humidity, soil_moisture, is_anomaly):
    db = None
    try:
        if not DB_NAME:
            raise ValueError("数据库名称未配置")

        db = psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
        cursor = db.cursor()
        # 不插入 id，让数据库自增
        sql = """
            INSERT INTO rawdata_from_sensors
            (sensor_id, time_stamp, temperature, humidity, soil_moisture, is_anomaly)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        cursor.execute(sql, (sensor_id, time_stamp,
                             temperature, humidity, soil_moisture, is_anomaly))
        new_id = cursor.fetchone()[0]
        db.commit()
        print(f"插入成功，生成的 id 为: {new_id}")
    except psycopg2.Error as e:
        logging.error(f"数据库错误: {e}")
        if db:
            db.rollback()
    except Exception as e:
        logging.error(f"保存到数据库失败: {e}")
    finally:
        if db:
            db.close()



def on_disconnect(client, userdata, flags, reason_code, properties):
    """修复：添加了 reason_code 和 properties 参数"""
    logging.warning(f"连接断开! 原因代码: {reason_code}. 尝试重连...")
    reconnect_delay = 1
    while True:
        try:
            client.reconnect()
            print("成功重连!")
            return
        except Exception as e:
            logging.error(f"重连失败: {e}")
            time.sleep(min(reconnect_delay, 60))
            reconnect_delay *= 2


def listening():
    client = mqtt.Client(client_id=CLIENT_ID, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    # 添加MQTT认证（如果需要）
    # client.username_pw_set("username", "password")

    # 启用TLS（如果需要）
    # client.tls_set()

    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    try:
        listening()
    except KeyboardInterrupt:
        print("程序被用户中断")
    except Exception as e:
        logging.error(f"程序异常终止: {e}")
