import threading
import listen

from database import db_manager

def main():
    print("programme running...")
    # 初始化数据库
    if not db_manager.initialize_database():
        print("❌ initializing failed, programme exits")
        return
    
    # 主程序逻辑
    print("🖥️ 应用程序运行中...")
    # 你的业务逻辑代码
    thread_listen = threading.Thread(target=listen.listening())
    #thread2 = threading.Thread(target=worker)

    thread_listen.start()
    
    print("🛑 应用程序结束")

if __name__ == "__main__":
    main()
