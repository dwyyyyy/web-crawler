"""
MySQL数据验证脚本
用于验证爬虫数据是否成功写入MySQL数据库
"""

import pymysql
from datetime import datetime


class MySQLDataVerifier:
    """MySQL数据验证工具类"""
    
    def __init__(self, host: str = 'localhost', port: int = 3306, 
                 user: str = 'root', password: str = '123456', 
                 database: str = 'pacong'):
        """
        初始化验证工具
        
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
        self.connection = None
    
    def connect(self) -> bool:
        """连接到数据库"""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            print(f"✅ 成功连接到MySQL数据库: {self.host}:{self.port}/{self.database}")
            return True
        except Exception as e:
            print(f"❌ 连接MySQL数据库失败: {e}")
            return False
    
    def verify_tables(self) -> bool:
        """验证表是否存在"""
        try:
            with self.connection.cursor() as cursor:
                # 检查商品表是否存在
                cursor.execute("SHOW TABLES LIKE 'commodities';")
                commodities_table = cursor.fetchone() is not None
                
                # 检查外汇表是否存在
                cursor.execute("SHOW TABLES LIKE 'forex_data';")
                forex_table = cursor.fetchone() is not None
                
                print(f"✅ 商品表 'commodities' {'存在' if commodities_table else '不存在'}")
                print(f"✅ 外汇表 'forex_data' {'存在' if forex_table else '不存在'}")
                
                return commodities_table
        except Exception as e:
            print(f"❌ 验证表存在性失败: {e}")
            return False
    
    def verify_commodity_data(self) -> bool:
        """验证商品数据是否存在"""
        try:
            with self.connection.cursor() as cursor:
                # 查询商品数据数量
                cursor.execute("SELECT COUNT(*) AS count FROM commodities;")
                result = cursor.fetchone()
                count = result['count'] if result else 0
                
                print(f"✅ 商品表中共有 {count} 条数据")
                
                # 如果有数据，查询最新的5条记录
                if count > 0:
                    cursor.execute("""
                        SELECT name, chinese_name, symbol, category, current_price, 
                               change_percent, source, timestamp 
                        FROM commodities 
                        ORDER BY timestamp DESC 
                        LIMIT 5;
                    """)
                    recent_data = cursor.fetchall()
                    
                    print(f"\n📋 最新的 {min(5, count)} 条商品数据:")
                    for i, item in enumerate(recent_data, 1):
                        print(f"  {i}. {item['name']} ({item.get('chinese_name', '')}): ")
                        print(f"     价格: {item['current_price']}")
                        print(f"     涨跌幅: {item['change_percent']}%")
                        print(f"     来源: {item['source']}")
                        print(f"     时间: {item['timestamp']}")
                        print(f"     分类: {item['category']}")
                
                return count > 0
        except Exception as e:
            print(f"❌ 验证商品数据失败: {e}")
            return False
    
    def get_data_summary(self) -> None:
        """获取数据摘要统计"""
        try:
            with self.connection.cursor() as cursor:
                # 按来源统计
                cursor.execute("""
                    SELECT source, COUNT(*) AS count 
                    FROM commodities 
                    GROUP BY source 
                    ORDER BY count DESC;
                """)
                source_stats = cursor.fetchall()
                
                # 按分类统计
                cursor.execute("""
                    SELECT category, COUNT(*) AS count 
                    FROM commodities 
                    GROUP BY category 
                    ORDER BY count DESC;
                """)
                category_stats = cursor.fetchall()
                
                print(f"\n📊 数据来源统计:")
                for item in source_stats:
                    print(f"  {item['source']}: {item['count']} 条")
                
                print(f"\n📊 商品分类统计:")
                for item in category_stats:
                    print(f"  {item['category']}: {item['count']} 条")
                
        except Exception as e:
            print(f"❌ 获取数据摘要失败: {e}")
    
    def verify_all(self) -> bool:
        """执行完整的验证流程"""
        print("=" * 60)
        print("🔍 开始MySQL数据验证")
        print("=" * 60)
        
        # 连接数据库
        if not self.connect():
            print("❌ 验证失败: 无法连接到MySQL数据库")
            return False
        
        try:
            # 验证表是否存在
            if not self.verify_tables():
                print("❌ 验证失败: 商品表不存在")
                return False
            
            # 验证数据是否存在
            if not self.verify_commodity_data():
                print("❌ 验证失败: 商品表中没有数据")
                return False
            
            # 获取数据摘要
            self.get_data_summary()
            
            print("=" * 60)
            print("✅ 数据验证成功！爬虫数据已成功写入MySQL数据库")
            print("=" * 60)
            return True
        finally:
            if self.connection:
                self.connection.close()
                print("已关闭数据库连接")


if __name__ == "__main__":
    # 创建验证实例并运行验证
    verifier = MySQLDataVerifier(
        host='localhost',
        port=3306,
        user='root',
        password='123456',
        database='pacong'
    )
    verifier.verify_all()