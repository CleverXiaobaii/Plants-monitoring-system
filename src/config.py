import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    # 数据库配置
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "1145")
    DB_NAME = os.getenv("DB_NAME", "PlantsMonitoringSystem")
    DB_USER = os.getenv("DB_USER", "user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "114514")

    # 连接字符串
    @property
    def DB_URL(self):
        return """your database url"""    #f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # 管理员连接字符串（用于创建数据库）
    @property
    def ADMIN_DB_URL(self):
        return """your admin database url"""    #f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/postgres"


config = Config()
