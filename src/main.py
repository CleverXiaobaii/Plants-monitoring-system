# main.py

import threading
import listen      # 负责从 Broker 拉数据写数据库
import calc        # 负责启动 Flask 服务，给前端提供 /sensor-data 接口
import database    # 或者叫 db_manager；负责 initialize_database()
import time
import sys

def main():
    print("programme running...")

    # 1. 初始化数据库
    if not database.db_manager.initialize_database():
        print("❌ initializing failed, programme exits")
        return

    # 2. 输出应用程序启动日志
    print("💻 应用程序运行中...")

    # 3. 启动 MQTT 监听线程
    thread_listen = threading.Thread(target=listen.listening)
    # （可选）让它随主线程一起退出：
    thread_listen.daemon = True

    # 4. 启动 calc（Flask 服务）线程
    thread_calc = threading.Thread(target=calc.main)
    thread_calc.daemon = True

    thread_listen.start()
    thread_calc.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 收到 Ctrl+C，正在退出…")
        sys.exit(0)

    # 5. 主线程若没有其它业务逻辑，可以直接一直休眠或 join
    #    可以用 .join() 让主线程等子线程结束（不过这两个子线程本身都不会自己结束）
    # thread_listen.join()
    # thread_calc.join()

    # 也可以不 join，让主线程到达末尾后保持进程存活即可
    print("🔴 应用程序结束（主线程继续保活，子线程依旧运行）")

if __name__ == "__main__":
    main()

