#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库功能测试脚本
用于测试基于数据库的三个主要功能：
1. 获取最新价格
2. 获取历史价格
3. 获取价格变更记录

使用方法：
1. 根据实际情况修改下面的数据库连接参数
2. 运行脚本：python test_db_functions.py
"""
import pymysql
from datetime import datetime, timedelta
import argparse

class DatabaseTester:
    def __init__(self, host='10.180.248.144', port=3306, user='root', password='cJHZQYR7ajrXZd', database='pacong'):
        """
        初始化数据库连接
        
        Args:
            host: MySQL主机地址
            port: MySQL端口
            user: MySQL用户名
            password: MySQL密码
            database: 数据库名
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        self.available_commodities = []
        
    def connect(self):
        """建立数据库连接"""
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
            print(f"✓ 成功连接到数据库: {self.host}:{self.port}/{self.database}")
            return True
        except Exception as e:
            print(f"✗ 数据库连接失败: {e}")
            return False
    
    def disconnect(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            print("已关闭数据库连接")
    
    def test_get_latest_price(self, commodity_name='黄金期货主力合约'):
        """测试获取最新价格功能"""
        if not self.connection:
            print("请先建立数据库连接")
            return
        
        try:
            with self.connection.cursor() as cursor:
                sql = """
                SELECT name, chinese_name, current_price, change_amount, change_percent, 
                       currency, source, version_ts 
                FROM commodity_latest 
                WHERE name = %s
                """
                print(f"\n测试获取最新价格 - 商品名称: {commodity_name}")
                cursor.execute(sql, (commodity_name,))
                result = cursor.fetchone()
                
                if result:
                    print("✓ 获取成功!")
                    # 格式化输出结果
                    for key, value in result.items():
                        if isinstance(value, datetime):
                            value = value.isoformat()
                        print(f"  {key}: {value}")
                else:
                    print(f"✗ 未找到商品 '{commodity_name}' 的最新价格数据")
        except Exception as e:
            print(f"✗ 查询失败: {e}")
    
    def print_database_stats(self):
        """打印数据库基本统计信息"""
        if not self.connection:
            print("请先建立数据库连接")
            return
        
        try:
            with self.connection.cursor() as cursor:
                print("\n=== 数据库统计信息 ===")
                
                # 统计commodity_latest表记录数
                cursor.execute("SELECT COUNT(*) as count FROM commodity_latest")
                latest_count = cursor.fetchone()['count']
                print(f"commodity_latest表记录数: {latest_count}")
                
                # 统计commodity_history表记录数
                cursor.execute("SELECT COUNT(*) as count FROM commodity_history")
                history_count = cursor.fetchone()['count']
                print(f"commodity_history表记录数: {history_count}")
                
                # 统计change_log表记录数
                cursor.execute("SELECT COUNT(*) as count FROM change_log")
                log_count = cursor.fetchone()['count']
                print(f"change_log表记录数: {log_count}")
                
                # 查询最新的记录时间
                cursor.execute("SELECT MAX(version_ts) as latest_time FROM commodity_latest")
                latest_time = cursor.fetchone()['latest_time']
                if latest_time:
                    print(f"最新数据更新时间: {latest_time.isoformat()}")
                
                print("=== 统计信息结束 ===")
        except Exception as e:
            print(f"✗ 获取数据库统计信息失败: {e}")
    
    def test_get_price_history(self, commodity_name='黄金期货主力合约', days=7):
        """测试获取历史价格功能"""
        if not self.connection:
            print("请先建立数据库连接")
            return
        
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            with self.connection.cursor() as cursor:
                sql = """
                SELECT name, current_price, change_percent, version_ts 
                FROM commodity_history 
                WHERE name = %s AND version_ts BETWEEN %s AND %s
                ORDER BY version_ts ASC
                """
                print(f"\n测试获取历史价格 - 商品名称: {commodity_name}, 时间范围: 最近{days}天")
                cursor.execute(sql, (commodity_name, start_time, end_time))
                results = cursor.fetchall()
                
                print(f"✓ 查询成功! 共返回 {len(results)} 条记录")
                # 打印前5条记录作为示例
                if results:
                    print("前5条记录示例:")
                    for i, record in enumerate(results[:5]):
                        print(f"  记录 {i+1}:")
                        for key, value in record.items():
                            if isinstance(value, datetime):
                                value = value.isoformat()
                            print(f"    {key}: {value}")
                else:
                    # 如果没有记录，尝试查看表中的所有记录
                    print("\n尝试查询该商品的所有历史记录...")
                    try:
                        sql_all = """
                        SELECT name, current_price, change_percent, version_ts 
                        FROM commodity_history 
                        WHERE name = %s
                        ORDER BY version_ts ASC
                        LIMIT 10
                        """
                        cursor.execute(sql_all, (commodity_name,))
                        results_all = cursor.fetchall()
                        print(f"该商品所有历史记录数: {len(results_all)}")
                        if results_all:
                            print("最新的3条历史记录:")
                            for i, record in enumerate(results_all[-3:]):
                                print(f"  记录 {i+1}:")
                                for key, value in record.items():
                                    if isinstance(value, datetime):
                                        value = value.isoformat()
                                    print(f"    {key}: {value}")
                    except Exception as e:
                        print(f"✗ 扩展查询失败: {e}")
        except Exception as e:
            print(f"✗ 查询失败: {e}")
    
    def test_get_price_changes(self, days=1):
        """测试获取价格变更记录功能"""
        if not self.connection:
            print("请先建立数据库连接")
            return
        
        try:
            start_time = datetime.now() - timedelta(days=days)
            
            with self.connection.cursor() as cursor:
                sql = """
                SELECT cl.name, cl.chinese_name, cl.currency, 
                       cl.current_price, cl.change_percent, cl.version_ts,
                       cl.source, cl.id as entity_id,
                       log.request_id, log.field_name, log.old_value, log.new_value, log.change_type
                FROM change_log log
                JOIN commodity_latest cl ON log.entity_id = cl.id
                WHERE log.version_ts >= %s
                ORDER BY log.version_ts DESC, log.log_id DESC
                LIMIT 100
                """
                print(f"\n测试获取价格变更记录 - 时间范围: 最近{days}天")
                cursor.execute(sql, (start_time,))
                results = cursor.fetchall()
                
                print(f"✓ 查询成功! 共返回 {len(results)} 条记录")
                # 打印前3条记录作为示例
                if results:
                    print("前3条记录示例:")
                    for i, record in enumerate(results[:3]):
                        print(f"  记录 {i+1}:")
                        # 只打印关键字段以避免输出过多
                        key_fields = ['name', 'chinese_name', 'field_name', 'old_value', 'new_value', 'version_ts']
                        for key in key_fields:
                            if key in record:
                                value = record[key]
                                if isinstance(value, datetime):
                                    value = value.isoformat()
                                print(f"    {key}: {value}")
                else:
                    # 如果没有记录，尝试查看更早的记录
                    print("\n尝试查询更长时间范围内的变更记录...")
                    try:
                        start_time = datetime.now() - timedelta(days=30) # 查询30天内的记录
                        sql = """
                        SELECT cl.name, cl.chinese_name, cl.currency, 
                               cl.current_price, cl.change_percent, cl.version_ts,
                               cl.source, cl.id as entity_id,
                               log.request_id, log.field_name, log.old_value, log.new_value, log.change_type
                        FROM change_log log
                        JOIN commodity_latest cl ON log.entity_id = cl.id
                        WHERE log.version_ts >= %s
                        ORDER BY log.version_ts DESC, log.log_id DESC
                        LIMIT 100
                        """
                        cursor.execute(sql, (start_time,))
                        results_30days = cursor.fetchall()
                        print(f"30天内共返回 {len(results_30days)} 条记录")
                    except Exception as e:
                        print(f"✗ 扩展查询失败: {e}")
        except Exception as e:
            print(f"✗ 查询失败: {e}")
    
    def get_available_commodities(self):
        """获取数据库中可用的商品名称列表"""
        if not self.connection:
            print("请先建立数据库连接")
            return []
        
        try:
            with self.connection.cursor() as cursor:
                sql = "SELECT DISTINCT name FROM commodity_latest LIMIT 10"
                cursor.execute(sql)
                results = cursor.fetchall()
                
                self.available_commodities = [row['name'] for row in results]
                print(f"\n数据库中可用的商品名称 ({len(self.available_commodities)} 个):")
                for i, name in enumerate(self.available_commodities):
                    print(f"  {i+1}. {name}")
                
                return self.available_commodities
        except Exception as e:
            print(f"✗ 获取商品列表失败: {e}")
            return []
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=== 开始数据库功能测试 ===")
        
        # 首先测试连接
        if not self.connect():
            print("数据库连接失败，无法继续测试")
            return
        
        try:
            # 获取可用的商品名称
            available_commodities = self.get_available_commodities()
            
            # 如果有可用商品，使用第一个商品进行测试
            test_commodity = available_commodities[0] if available_commodities else '黄金期货主力合约'
            print(f"\n使用商品 '{test_commodity}' 进行测试")
            
            # 测试三个主要功能
            self.test_get_latest_price(test_commodity)
            self.test_get_price_history(test_commodity)
            self.test_get_price_changes()
            
            # 打印数据库统计信息
            self.print_database_stats()
        finally:
            # 确保关闭连接
            self.disconnect()
        
        print("\n=== 测试完成 ===")

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='测试数据库功能')
    parser.add_argument('--host', type=str, default='10.180.248.144', help='MySQL主机地址')
    parser.add_argument('--port', type=int, default=3306, help='MySQL端口')
    parser.add_argument('--user', type=str, default='root', help='MySQL用户名')
    parser.add_argument('--password', type=str, default='cJHZQYR7ajrXZd', help='MySQL密码')
    parser.add_argument('--database', type=str, default='pacong', help='数据库名')
    args = parser.parse_args()
    
    # 创建测试实例并运行测试
    tester = DatabaseTester(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database
    )
    
    tester.run_all_tests()