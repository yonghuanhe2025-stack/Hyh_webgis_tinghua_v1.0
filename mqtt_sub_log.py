# -*- coding: utf-8 -*-
import paho.mqtt.client as mqtt
import os
import signal
import sys
import atexit
from datetime import datetime

# MQTT 服务器信息
MQTT_BROKER = "47.101.130.178"
MQTT_PORT = 9003
MQTT_USER = "tsari"
MQTT_PASS = "tsari123"
MQTT_TOPIC = "/dtu_serial_rx"

# 程序启动时的日志文件（临时名）
LOG_FILE = os.path.join(os.path.dirname(__file__), "mqtt_log_running.txt")


# === 退出时执行的函数 ===
def finalize_log():
    """在程序结束时重命名日志文件"""
    if os.path.exists(LOG_FILE):
        end_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = os.path.join(os.path.dirname(__file__), f"mqtt_log_{end_time}.txt")
        os.rename(LOG_FILE, new_name)
        print(f"\n📝 日志已保存为: {new_name}")


# 注册退出事件
atexit.register(finalize_log)
signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))  # Ctrl+C 捕获
signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))  # kill 捕获


# 连接回调
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ 已连接到 MQTT 服务器")
        client.subscribe(MQTT_TOPIC)  # 订阅主题
        print(f"📡 已订阅主题: {MQTT_TOPIC}")
        print(f"📝 日志文件(运行中): {LOG_FILE}")
    else:
        print(f"❌ 连接失败，错误码: {rc}")


# 消息回调
def on_message(client, userdata, msg):
    message = msg.payload.decode("utf-8", errors="ignore")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {msg.topic} -> {message}\n"

    # 打印到终端
    print(f"📩 {log_entry.strip()}")

    # 写入临时日志文件
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)


def main():
    # 创建客户端
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASS)  # 设置用户名和密码
    client.on_connect = on_connect
    client.on_message = on_message

    # 连接服务器
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    # 循环等待消息
    client.loop_forever()


if __name__ == "__main__":
    main()
