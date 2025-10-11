"""
MySQL连接测试脚本
用于验证MySQL数据库连接和写入功能是否正常
"""

import pymysql
from datetime import datetime
from typing import Optional


class MySQLTest:
    """MySQL连接测试工具类"""
    
    def __init__(self, host: str = 'localhost', port: int = 3306, 
                 user: str = 'root', password: str = '123456', 
                 database: str = 'pacong'):
        """
        初始化测试工具
        
        Args:
            host: MySQL主机地址
            port: MySQL端口
            user: MySQL用户名
            password: MySQL密码
            database: MySQL数据库名
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection: Optional[pymysql.Connection] = None
    
    def test_connection(self) -> bool:
        """测试数据库连接是否正常"""
        try:
            # 先尝试不指定数据库连接
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                charset='utf8mb4'
            )
            
            # 创建数据库（如果不存在）
            with self.connection.cursor() as cursor:
                create_db_sql = f"CREATE DATABASE IF NOT EXISTS {self.database} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
                cursor.execute(create_db_sql)
                print(f"✅ 数据库 '{self.database}' 已创建或已存在")
                
                # 选择数据库
                cursor.execute(f"USE {self.database};")
                print(f"✅ 已选择数据库: {self.database}")
            
            return True
        except Exception as e:
            print(f"❌ 连接MySQL数据库失败: {e}")
            return False
        finally:
            if self.connection:
                self.connection.close()
                print("已关闭数据库连接")
    
    def create_test_database(self) -> bool:
        """创建测试数据库（如果不存在）"""
        try:
            # 先不指定数据库连接
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                charset='utf8mb4'
            )
            
            with self.connection.cursor() as cursor:
                # 创建数据库（如果不存在）
                create_db_sql = f"CREATE DATABASE IF NOT EXISTS {self.database} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
                cursor.execute(create_db_sql)
                print(f"✅ 数据库 '{self.database}' 已创建或已存在")
                
                # 选择数据库
                cursor.execute(f"USE {self.database};")
                
                # 创建测试表
                create_test_table_sql = """
                CREATE TABLE IF NOT EXISTS test_connection (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    test_data VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
                cursor.execute(create_test_table_sql)
                print("✅ 测试表 'test_connection' 已创建或已存在")
                
                # 插入测试数据
                test_data = f"Test data at {datetime.now()}"
                insert_sql = "INSERT INTO test_connection (test_data) VALUES (%s);"
                cursor.execute(insert_sql, (test_data,))
                self.connection.commit()
                print(f"✅ 已插入测试数据: {test_data}")
                
                # 查询测试数据
                select_sql = "SELECT * FROM test_connection ORDER BY created_at DESC LIMIT 1;"
                cursor.execute(select_sql)
                result = cursor.fetchone()
                if result:
                    print(f"✅ 查询测试数据成功: {result}")
                
            return True
        except Exception as e:
            print(f"❌ 创建测试数据库或表失败: {e}")
            if self.connection:
                self.connection.rollback()
            return False
        finally:
            if self.connection:
                self.connection.close()
                print("已关闭数据库连接")
    
    def run_full_test(self) -> bool:
        """运行完整测试"""
        print("=" * 50)
        print("🔍 开始MySQL连接和写入测试")
        print("=" * 50)
        
        # 测试连接
        if not self.test_connection():
            print("❌ 测试失败: 无法连接到MySQL数据库")
            return False
        
        # 测试数据库创建和写入
        if not self.create_test_database():
            print("❌ 测试失败: 无法创建数据库或写入测试数据")
            return False
        
        print("=" * 50)
        print("✅ 所有测试通过！MySQL连接和写入功能正常")
        print("=" * 50)
        return True


if __name__ == "__main__":
    # 创建测试实例并运行测试
    mysql_test = MySQLTest(
        host='localhost',
        port=3306,
        user='root',
        password='123456',
        database='pacong'
    )
    mysql_test.run_full_test()