import os
import time
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from config import config


class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.initialized = False

    def connect(self, url=None):
        """连接到数据库"""
        if url is None:
            url = config.DB_URL

        max_retries = 5
        for i in range(max_retries):
            try:
                self.conn = psycopg2.connect(url)
                print("✅ succeeded connecting to PostgreSQL database")
                return True
            except psycopg2.OperationalError as e:
                if i < max_retries - 1:
                    print(f"⚠️ connecting failed，retrying... ({i + 1}/{max_retries})")
                    time.sleep(2 * (i + 1))
                else:
                    print(f"❌ unable to connect to the database: {e}")
                    return False

    def create_database(self):
        """创建数据库（如果不存在）"""
        try:
            # 连接到默认数据库
            self.connect(config.ADMIN_DB_URL)

            # 设置自动提交
            self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = self.conn.cursor()

            # 检查数据库是否存在
            cursor.execute(
                sql.SQL("SELECT 1 FROM pg_database WHERE datname = {}")
                .format(sql.Literal(config.DB_NAME))
            )
            exists = cursor.fetchone()

            if not exists:
                print(f"create database: {config.DB_NAME}")
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}")
                    .format(sql.Identifier(config.DB_NAME))
                )
                print("database creating success")
            else:
                print(f"database exists: {config.DB_NAME}")

            cursor.close()
            return True
        except Exception as e:
            print(f"database creating failed: {e}")
            return False
        finally:
            if self.conn:
                self.conn.close()

    def execute_sql_file(self, file_path):
        """执行SQL文件"""
        try:
            self.connect()
            cursor = self.conn.cursor()

            # 读取SQL文件
            with open(file_path, 'r') as f:
                sql_commands = f.read()

            # 执行SQL命令
            cursor.execute(sql_commands)
            self.conn.commit()
            print(f"executing sql file success: {os.path.basename(file_path)}")
            return True
        except Exception as e:
            print(f"executing sql file failed: {e}")
            return False
        finally:
            if cursor:
                cursor.close()

    def check_tables(self):
        """检查必要的表是否存在"""
        required_tables = ["rawdata_from_sensors", "plants"]  # 根据你的应用修改

        try:
            self.connect()
            cursor = self.conn.cursor()

            # 检查表是否存在
            for table in required_tables:
                cursor.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)",
                    (table,)
                )
                exists = cursor.fetchone()[0]
                if not exists:
                    print(f"table not exists: {table}")
                    return False

            print("all tables exist")
            return True
        except Exception as e:
            print(f"failed to check tables: {e}")
            return False
        finally:
            if cursor:
                cursor.close()

    def initialize_database(self):
        """初始化数据库"""
        # 创建数据库
        if not self.create_database():
            return False

        # 连接到新数据库
        if not self.connect():
            return False

        # 检查表是否存在
        if self.check_tables():
            print("database initialized")
            return True

        # 执行初始化脚本
        print("initializing...")
        schema_path = os.path.join(os.path.dirname(__file__), "..", "sql", "schema.sql")
        if self.execute_sql_file(schema_path):
            # 执行初始化数据脚本
            init_path = os.path.join(os.path.dirname(__file__), "..", "sql", "init.sql")
            self.execute_sql_file(init_path)
            print("initializing success!")
            return True

        return False


# 全局数据库管理器实例
db_manager = DatabaseManager()