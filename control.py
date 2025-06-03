#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
batch_control_sender.py

集成“按键控制环境趋势”与“每隔 interval 秒批量发布 30 个传感器状态”功能的脚本。

- 按 t：切换温度趋势（0 → +1 → −1 → 0 循环）
- 按 h：切换湿度趋势（0 → +1 → −1 → 0 循环）
- 按 s：切换土壤湿度趋势（0 → +1 → −1 → 0 循环）
- 按 q：立即退出程序

每隔 interval 秒：
  1. 按当前趋势更新基准值（温度/湿度/土壤含水量）
  2. 生成 30 条带随机噪声与小概率异常的数据
  3. 将这 30 条构成的 JSON 数组发布到 MQTT Broker
"""

import json
import time
import datetime
import threading
import argparse
import os

import numpy as np
import paho.mqtt.client as mqtt

# Windows 平台下捕获按键
import msvcrt


# ─── 参数默认值 ───────────────────────────────────────────────────────────
DEFAULT_BROKER      = "test.mosquitto.org"
DEFAULT_PORT        = 1883
DEFAULT_TOPIC       = "greenhouse/sensors"
NUM_SENSORS         = 30
ANOMALY_RATE        = 0.05        # 5% 几率注入异常
INTERVAL_SECONDS    = 10          # 每隔多少秒生成并发布一批数据

# 环境基准初始值（可以根据需要调整）
base_temperature    = 25.0        # 初始温度（℃）
base_humidity       = 60.0        # 初始湿度（%RH）
base_soil_moisture  = 500.0       # 初始土壤含水量（单位可自由定义）

# 趋势标记：-1 表示下降，0 表示保持，+1 表示上升
temp_trend  = 0
hum_trend   = 0
soil_trend  = 0

# 每秒变化速率
TEMP_RATE   = 0.5   # 温度每秒上下浮动 0.5 ℃
HUM_RATE    = 1.0   # 湿度每秒上下浮动 1 %
SOIL_RATE   = 5.0   # 土壤含水量每秒上下浮动 5 单位
# ────────────────────────────────────────────────────────────────────────────


def print_instructions():
    """
    启动时打印操作说明，让用户知道 t/h/s/q 对应什么功能。
    """
    msg = f"""
============ 环境仿真控制＋批量发布（每 {INTERVAL_SECONDS} 秒） ============

命令键说明（在此窗口按一次即可触发，不需回车）：
  t  → 切换 温度（Temperature） 的趋势：
         0 (静止) → +1 (上升) → -1 (下降) → 0 (停止) 循环
  h  → 切换 湿度（Humidity） 的趋势：同上逻辑。
  s  → 切换 土壤含水量（Soil Moisture） 的趋势：同上逻辑。
  q  → 退出程序（立即结束所有线程并断开 MQTT 连接）。

脚本功能：
  • 每隔 {INTERVAL_SECONDS} 秒，根据上述趋势更新“基准温度/湿度/土壤含水量”
  • 模拟 30 个传感器读数（随机噪声 + 小概率异常），打包成 JSON 数组
  • 将整个 JSON 数组一次性发布到 MQTT 主题 '{DEFAULT_TOPIC}'
  • 同时在控制台输出一次平均值示例与趋势状态

示例输出格式（每 {INTERVAL_SECONDS} 秒一次）：
  [2025-06-03 12:00:10]  Avg Temp: 25.54 ℃, Avg Hum: 60.12 %RH, Avg Soil: 502.30 | Trends: T=+1, H=0, S=-1

==============================================================================

    """
    print(msg)


def key_listener_loop():
    """
    持续监听按键（非阻塞），并根据按键更新对应的全局趋势标记：
      t→temp_trend, h→hum_trend, s→soil_trend, q→退出程序。
    """
    global temp_trend, hum_trend, soil_trend

    while True:
        if msvcrt.kbhit():
            ch = msvcrt.getch().decode("utf-8", errors="ignore").lower()

            if ch == "t":
                temp_trend = {0: 1, 1: -1, -1: 0}[temp_trend]
                print(f"🌡 温度趋势已切换为 {temp_trend:+d}")
            elif ch == "h":
                hum_trend = {0: 1, 1: -1, -1: 0}[hum_trend]
                print(f"💧 湿度趋势已切换为 {hum_trend:+d}")
            elif ch == "s":
                soil_trend = {0: 1, 1: -1, -1: 0}[soil_trend]
                print(f"🌱 土壤含水量趋势已切换为 {soil_trend:+d}")
            elif ch == "q":
                print("🏁 检测到 'q'，脚本即将退出。")
                os._exit(0)

        # 为了不让 CPU 占用过高，稍微睡眠一下
        time.sleep(0.1)


def generate_and_publish_loop(broker: str, port: int, topic: str, interval: int):
    """
    主循环：每隔 interval 秒执行以下步骤：
      1. 根据当前 temp_trend / hum_trend / soil_trend 更新基准值
      2. 生成 NUM_SENSORS 条传感器读数，带随机噪声与小概率异常标记
      3. 打包成一个 JSON 数组并发布到 MQTT
      4. 在控制台打印一次示例平均值与当前趋势状态
    """
    global base_temperature, base_humidity, base_soil_moisture
    global temp_trend, hum_trend, soil_trend

    # 先生成 1~NUM_SENSORS 的整型传感器 ID 列表
    sensor_ids = list(range(1, NUM_SENSORS + 1))

    # 初始化并连接 MQTT 客户端
    client = mqtt.Client()
    try:
        client.connect(broker, port)
    except Exception as e:
        print(f"[Error] 无法连接到 MQTT Broker {broker}:{port} → {e}")
        os._exit(1)

    client.loop_start()
    print(f"[Info] 已连接到 MQTT Broker：{broker}:{port}，主题：'{topic}'，每 {interval} 秒发布一次。\n")

    try:
        while True:
            # 1. 更新基准值
            base_temperature   += temp_trend * TEMP_RATE * interval
            base_humidity      += hum_trend  * HUM_RATE  * interval
            base_soil_moisture += soil_trend * SOIL_RATE * interval

            # 2. 生成本轮 30 条数据
            timestamp = datetime.datetime.now().replace(microsecond=0).isoformat()
            batch = []

            for sid in sensor_ids:
                # 每个传感器：在基准值基础上加随机噪声
                t = base_temperature + np.random.normal(0, 1.5)
                h = base_humidity    + np.random.normal(0, 5)
                s = base_soil_moisture + np.random.normal(0, 30)

                is_anomaly = False
                if np.random.rand() < ANOMALY_RATE:
                    is_anomaly = True
                    typ = np.random.choice(["temp_high", "humidity_low", "soil_dry"])
                    if typ == "temp_high":
                        t += np.random.uniform(10, 15)
                    elif typ == "humidity_low":
                        h -= np.random.uniform(30, 50)
                    else:  # soil_dry
                        s -= np.random.uniform(200, 300)
                        s = max(s, 0)

                record = {
                    "sensor_id": sid,
                    "timestamp": timestamp,
                    "temperature": round(t, 2),
                    "humidity":    round(h, 2),
                    "soil_moisture": int(s),
                    "is_anomaly":  is_anomaly
                }
                batch.append(record)

            # 3. 发布整批 JSON
            try:
                payload = json.dumps(batch, ensure_ascii=False)
            except (TypeError, ValueError) as err:
                print(f"[Warning] 序列化本批数据为 JSON 失败：{err}，跳过本轮发布。")
            else:
                client.publish(topic, payload)

            # 4. 在控制台打印一次“示例平均值 + 当前趋势”
            avg_temp  = np.mean([r["temperature"]  for r in batch])
            avg_hum   = np.mean([r["humidity"]     for r in batch])
            avg_soil  = np.mean([r["soil_moisture"] for r in batch])
            now_str   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            trend_info = f"T={temp_trend:+d}, H={hum_trend:+d}, S={soil_trend:+d}"
            print(f"[{now_str}]  Avg Temp: {avg_temp:5.2f} ℃, "
                  f"Avg Hum: {avg_hum:5.2f} %RH, Avg Soil: {avg_soil:5.2f}  | Trends: {trend_info}")

            # 5. 等待下一个周期
            time.sleep(interval)

    except KeyboardInterrupt:
        # 捕获 Ctrl+C 强制退出
        print("\n[Info] 收到 Ctrl+C，停止发布并断开连接。")
    finally:
        time.sleep(0.5)
        client.loop_stop()
        client.disconnect()
        print("[Info] MQTT 客户端已断开连接，程序退出。")
        os._exit(0)


def parse_args():
    """
    解析命令行参数，允许指定 broker/port/topic/interval 等。
    """
    parser = argparse.ArgumentParser(
        description="带按键控制趋势的批量传感器发布脚本"
    )
    parser.add_argument(
        "--broker", "-b", type=str, default=DEFAULT_BROKER,
        help=f"MQTT Broker 地址（默认 {DEFAULT_BROKER}）"
    )
    parser.add_argument(
        "--port", "-p", type=int, default=DEFAULT_PORT,
        help=f"MQTT Broker 端口（默认 {DEFAULT_PORT}）"
    )
    parser.add_argument(
        "--topic", "-t", type=str, default=DEFAULT_TOPIC,
        help=f"发布主题（默认 {DEFAULT_TOPIC}）"
    )
    parser.add_argument(
        "--interval", "-i", type=int, default=INTERVAL_SECONDS,
        help=f"批量发送间隔（秒）（默认 {INTERVAL_SECONDS} 秒）"
    )
    return parser.parse_args()


if __name__ == "__main__":
    # 1. 打印操作说明
    print_instructions()

    # 2. 启动按键监听线程
    listener_thread = threading.Thread(target=key_listener_loop, daemon=True)
    listener_thread.start()

    # 3. 解析命令行参数并进入主循环
    args = parse_args()
    generate_and_publish_loop(
        broker=args.broker,
        port=args.port,
        topic=args.topic,
        interval=args.interval
    )
