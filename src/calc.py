# =========================================
# src/calc.py
# =========================================

# src/calc.py

from flask import Flask, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

# 使用你已有的 config.py。它在模块底部实例化了一个名为 config 的对象
from config import config

app = Flask(__name__)

def get_db_cursor():
    """
    建立一个 psycopg2 连接，并返回 (conn, cursor)。
    采用 RealDictCursor，fetchall()/fetchone() 直接返回 dict，方便 jsonify。
    """
    conn = psycopg2.connect(
        host     = config.DB_HOST,
        port     = config.DB_PORT,
        dbname   = config.DB_NAME,
        user     = config.DB_USER,
        password = config.DB_PASSWORD
    )
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=RealDictCursor)
    return conn, cur

@app.route('/sensor-data', methods=['GET'])
def sensor_data():
    """
    前端每隔几秒轮询一次，拿到所有传感器的最新值 + 24h 历史 + 告警列表，
    并对 soil_moisture 从原始 ADC 值 (0–1023) 转换为百分比 (0–100)。
    """
    conn, cur = get_db_cursor()
    try:
        # 1) 拿到所有 distinct 的 sensor_id
        cur.execute("SELECT DISTINCT sensor_id FROM rawdata_from_sensors;")
        rows = cur.fetchall()
        sensor_ids = [row['sensor_id'] for row in rows]

        result_list = []
        now_utc = datetime.utcnow()

        for sid in sensor_ids:
            # 2) 查询最新一条记录
            cur.execute("""
                SELECT *
                  FROM rawdata_from_sensors
                 WHERE sensor_id = %s
              ORDER BY time_stamp DESC
                 LIMIT 1
            """, (sid,))
            latest = cur.fetchone()
            if not latest:
                continue

            # 3) 查询过去 24h 内最新 24 条记录
            time_24h_ago = now_utc - timedelta(hours=24)
            cur.execute("""
                SELECT temperature, humidity, soil_moisture, time_stamp, is_anomaly
                  FROM rawdata_from_sensors
                 WHERE sensor_id = %s
                   AND time_stamp >= %s
              ORDER BY time_stamp DESC
                 LIMIT 24
            """, (sid, time_24h_ago))
            last24 = cur.fetchall()
            # 倒序 → 正序 (从最早到最新)
            last24.reverse()

            temp_hist = []
            hum_hist = []
            soil_hist = []
            alerts = []

            # 4) 遍历历史记录，推入折线图数组，并收集告警
            for rec in last24:
                temp_hist.append(float(rec["temperature"]))
                hum_hist.append(float(rec["humidity"]))

                # 原始 soil_moisture → 百分比
                raw_sm = float(rec["soil_moisture"])
                sm_percent = raw_sm / 1023 * 100
                soil_hist.append(round(sm_percent, 2))

                if rec["is_anomaly"]:
                    alerts.append({
                        "time": rec["time_stamp"].isoformat(),
                        "level": "warning",
                        "message": "检测到异常"
                    })

            # 如果最新那条本身也是告警，要插在最前
            if latest["is_anomaly"]:
                alerts.insert(0, {
                    "time": latest["time_stamp"].isoformat(),
                    "level": "warning",
                    "message": "检测到异常"
                })

            # 5) 处理最新值的转换
            # 最新 soil_moisture 原始读数 → 百分比
            raw_latest_sm = float(latest["soil_moisture"])
            latest_sm_percent = raw_latest_sm / 1023 * 100

            sensor_obj = {
                # 前端 plantData.plants[].id 使用 "plant-<sid>"
                "sensor_id": f"plant-{sid}",

                # 当前值
                "timestamp": latest["time_stamp"].isoformat(),
                "temperature": float(latest["temperature"]),
                "humidity": float(latest["humidity"]),
                "soil_moisture": round(latest_sm_percent, 2),
                "is_anomaly": bool(latest["is_anomaly"]),

                # 24h 历史
                "temperature_history": temp_hist,
                "humidity_history": hum_hist,
                "soil_moisture_history": soil_hist,

                # 告警列表
                "alerts": alerts
            }
            result_list.append(sensor_obj)

        cur.close()
        conn.close()

        return jsonify(result_list)

    except Exception as e:
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

def main():
    """
    可直接 `python calc.py` 启动，对外暴露 /sensor-data 接口。
    建议生产环境使用 WSGI 服务器，这里仅用于开发调试。
    """
    # 如果你仍要 file:// 打开前端页面，请启用以下 CORS：
    # from flask_cors import CORS
    # CORS(app)

    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    main()
