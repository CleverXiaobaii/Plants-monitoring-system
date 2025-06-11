# ==========================================
# listen.py (改良示例)
# ==========================================
import os
import json
import time
import logging
from dotenv import load_dotenv

import paho.mqtt.client as mqtt
import psycopg2
from psycopg2 import pool

# -------------------------------------------------
# 1. 从环境变量中读取 DB/MQTT 配置
# -------------------------------------------------
load_dotenv()

MQTT_BROKER = os.getenv("MQTT_BROKER", "test.mosquitto.org")
MQTT_PORT   = int(os.getenv("MQTT_PORT", 1883))
TOPIC       = os.getenv("MQTT_TOPIC", "greenhouse/#")
CLIENT_ID   = os.getenv("MQTT_CLIENT_ID", "mqtt-listener")

DB_HOST     = os.getenv("DB_HOST", "innovatinsa.piwio.fr")
DB_PORT     = int(os.getenv("DB_PORT", 5432))
DB_NAME     = os.getenv("DB_NAME", "group02")
DB_USER     = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "innovatinsa-piwio-5432")

# -------------------------------------------------
# 2. 初始化日志
# -------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# -------------------------------------------------
# 3. 创建一个简单的连接池，供整个脚本复用
#    （避免频繁 open/close）
# -------------------------------------------------
db_pool = None
def init_db_pool():
    global db_pool
    if db_pool is None:
        try:
            db_pool = psycopg2.pool.SimpleConnectionPool(
                1,    # 最小连接数
                5,    # 最大连接数
                host     = DB_HOST,
                port     = DB_PORT,
                database = DB_NAME,
                user     = DB_USER,
                password = DB_PASSWORD
            )
            logging.info("✅ 数据库连接池已初始化")
        except Exception as e:
            logging.error(f"数据库连接池初始化失败: {e}")
            raise

# -------------------------------------------------
# 4. 插入一条传感器数据到 rawdata_from_sensors 表
# -------------------------------------------------
def save_to_db(sensor_id, time_stamp, temperature, humidity, soil_moisture, is_anomaly):
    """
    用连接池取一个连接，插入一条记录。
    遇到任何错误先 rollback，再把连接还回去。
    """
    conn = None
    cursor = None
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        sql = """
            INSERT INTO rawdata_from_sensors
            (sensor_id, time_stamp, temperature, humidity, soil_moisture, is_anomaly)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        # 如果 time_stamp 是字符串，确保数据库列可接受 ISO 格式，或自行先 parse
        cursor.execute(sql, (sensor_id, time_stamp,
                             temperature, humidity, soil_moisture, is_anomaly))
        new_id = cursor.fetchone()[0]
        conn.commit()
        logging.info(f"插入成功，ID={new_id}, sensor_id={sensor_id}")
    except psycopg2.Error as e:
        logging.error(f"PostgreSQL 插入失败: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        logging.error(f"save_to_db 出现异常: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            db_pool.putconn(conn)

# -------------------------------------------------
# 5. MQTT 回调：
#    - on_connect: 连接成功后订阅
#    - on_message: 收到消息并保存到 DB
#    - on_disconnect: 尝试重连
# -------------------------------------------------
def on_connect(client, userdata, flags, reason_code, properties=None):
    """
    Paho v1.5.x 下是 (client, userdata, flags, rc)，properties=None 兼容旧版；
    Paho v1.6+ 下是 (client, userdata, flags, reason_code, properties)
    """
    if reason_code == 0:
        logging.info("✅ 连接到 MQTT Broker 成功")
        client.subscribe(TOPIC, qos=1)
    else:
        logging.error(f"❌ 连接失败，返回码: {reason_code}")

def on_message(client, userdata, msg):
    """
    当收到消息时，会进入这里。
    msg.payload 是 bytes，需要 decode 后做 json.loads
    """
    try:
        raw = msg.payload.decode('utf-8')
        payload = json.loads(raw)
    except json.JSONDecodeError:
        logging.error(f"❌ JSON 解析失败: topic={msg.topic}, payload={msg.payload}")
        return
    except Exception as e:
        logging.error(f"❌ 无法解码消息: {e}")
        return

    # 解析必需字段
    sensor_id    = payload.get("sensor_id")
    time_stamp   = payload.get("timestamp")
    temperature  = payload.get("temperature")
    humidity     = payload.get("humidity")
    soil_moisture= payload.get("soil_moisture")
    is_anomaly   = payload.get("is_anomaly", False)

    # 校验字段完整性（简单示例，可根据需求再加强）
    if sensor_id is None or time_stamp is None:
        logging.error(f"❌ 必需字段缺失: {payload}")
        return

    save_to_db(sensor_id, time_stamp, temperature, humidity, soil_moisture, is_anomaly)

def on_disconnect(client, userdata, reason_code, properties=None):
    """
    同样做成兼容 Paho v1.5/v1.6+ 的形式。
    如果断开连接，就尝试不断重连。
    """
    logging.warning(f"⚠️ 连接断开！ code={reason_code}，开始尝试重连...")
    delay = 1
    while True:
        try:
            client.reconnect()
            logging.info("✅ 重连成功")
            return
        except Exception as e:
            logging.error(f"❌ 重连失败：{e}，{delay}s 后再次尝试")
            time.sleep(min(delay, 60))
            delay *= 2

# -------------------------------------------------
# 6. listening() 主函数：初始化 DB 池 + 连接 MQTT + loop_forever()
# -------------------------------------------------
def listening():
    # 先初始化数据库连接池
    init_db_pool()

    # 再创建 MQTT 客户端
    client = mqtt.Client(
        client_id=CLIENT_ID,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2  # 如果你确定是 paho>=1.6
    )
    client.on_connect    = on_connect
    client.on_message    = on_message
    client.on_disconnect = on_disconnect

    # 如果你的 Broker 需要用户名/密码、TLS 等，都在这里设置：
    # client.username_pw_set("username", "password")
    # client.tls_set(...)

    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    logging.info(f"📡 已连接 MQTT Broker {MQTT_BROKER}:{MQTT_PORT}，开始循环订阅 {TOPIC}")
    client.loop_forever()

# -------------------------------------------------
# 7. 脚本可直接独立运行或被 main.py 以线程方式调用
# -------------------------------------------------
if __name__ == "__main__":
    try:
        listening()
    except KeyboardInterrupt:
        logging.info("⚙️ 程序被用户终止")
    except Exception as e:
        logging.error(f"🔴 程序异常终止: {e}")
