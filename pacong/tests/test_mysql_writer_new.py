"""
测试新的MySQLWriter实现"""

import unittest
from datetime import datetime
import random
import time

from ..output.mysql_writer import MySQLWriter
from ..data.models import CommodityData


class TestMySQLWriterNew(unittest.TestCase):
    """测试新的MySQLWriter实现"""
    
    def setUp(self):
        """设置测试环境"""
        self.writer = MySQLWriter(
            host='localhost',
            port=3306,
            user='root',
            password='123456',
            database='pacong_test'
        )
        
        # 确保测试表存在
        self.writer._connect()
        with self.writer.connection.cursor() as cursor:
            # 删除旧的测试表（如果存在）
            cursor.execute("DROP TABLE IF EXISTS commodity_latest, commodity_history, change_log")
            self.writer.connection.commit()
        self.writer._disconnect()
        
        # 重新创建表结构
        self.writer._create_tables()
    
    def tearDown(self):
        """清理测试环境"""
        # 可选：测试完成后删除测试表
        # self.writer._connect()
        # with self.writer.connection.cursor() as cursor:
        #     cursor.execute("DROP TABLE IF EXISTS commodity_latest, commodity_history, change_log")
        #     self.writer.connection.commit()
        # self.writer._disconnect()
        pass
    
    def test_write_commodity_data(self):
        """测试写入商品数据"""
        # 创建测试数据
        test_commodities = [
            CommodityData(
                name=f"Test Commodity {i}",
                value=random.uniform(10, 1000),  # 显式提供value参数
                chinese_name=f"测试商品 {i}",
                symbol=f"TEST{i}",
                category="测试分类",
                current_price=random.uniform(10, 1000),
                change_percent=random.uniform(-5, 5),
                source="test_source",
                timestamp=datetime.now()
            ) for i in range(3)
        ]
        
        # 写入数据
        result = self.writer.write_commodity_data(test_commodities)
        self.assertTrue(result)
        
        # 验证数据是否写入成功
        self.writer._connect()
        with self.writer.connection.cursor() as cursor:
            # 检查快照表
            cursor.execute("SELECT COUNT(*) as count FROM commodity_latest")
            latest_count = cursor.fetchone()['count']
            self.assertEqual(latest_count, 3)
            
            # 检查历史表
            cursor.execute("SELECT COUNT(*) as count FROM commodity_history")
            history_count = cursor.fetchone()['count']
            self.assertEqual(history_count, 3)
            
            # 检查变更日志
            cursor.execute("SELECT COUNT(*) as count FROM change_log")
            log_count = cursor.fetchone()['count']
            self.assertEqual(log_count, 3)  # 每个插入对应一条日志
        
    def test_update_commodity_data(self):
        """测试更新商品数据"""
        # 创建初始测试数据
        initial_commodities = [
            CommodityData(
                name="Update Test Commodity",
                value=100.0,  # 显式提供value参数
                chinese_name="更新测试商品",
                symbol="UPDATE_TEST",
                category="测试分类",
                current_price=100.0,
                change_percent=0.0,
                source="test_source",
                timestamp=datetime.now()
            )
        ]
        
        # 写入初始数据
        self.writer.write_commodity_data(initial_commodities)
        
        # 等待一小段时间，确保时间戳不同
        time.sleep(1)
        
        # 创建更新的数据
        updated_commodities = [
            CommodityData(
                name="Update Test Commodity",
                value=150.0,  # 显式提供value参数
                chinese_name="更新测试商品",
                symbol="UPDATE_TEST",
                category="测试分类",
                current_price=150.0,  # 价格发生变化
                change_percent=50.0,  # 变化率发生变化
                source="test_source",
                timestamp=datetime.now()
            )
        ]
        
        # 更新数据
        result = self.writer.write_commodity_data(updated_commodities)
        self.assertTrue(result)
        
        # 验证更新是否成功
        self.writer._connect()
        with self.writer.connection.cursor() as cursor:
            # 检查快照表中的数据是否已更新
            cursor.execute("SELECT current_price, change_percent FROM commodity_latest WHERE name = %s", 
                          ("Update Test Commodity",))
            latest_data = cursor.fetchone()
            self.assertEqual(latest_data['current_price'], 150.0)
            self.assertEqual(latest_data['change_percent'], 50.0)
            
            # 检查历史表中是否有两条记录
            cursor.execute("SELECT COUNT(*) as count FROM commodity_history WHERE name = %s", 
                          ("Update Test Commodity",))
            history_count = cursor.fetchone()['count']
            self.assertEqual(history_count, 2)
            
            # 检查变更日志中是否有两条变更记录
            cursor.execute("SELECT COUNT(*) as count FROM change_log WHERE entity_type = 'commodity' AND field_name != 'entity' AND field_name != 'name' AND field_name != 'source'")
            log_count = cursor.fetchone()['count']
            self.assertEqual(log_count, 2)  # 价格和变化率各一条日志
    
    def test_late_data_handling(self):
        """测试迟到数据的处理"""
        # 创建初始测试数据（当前时间）
        initial_commodities = [
            CommodityData(
                name="Late Data Test",
                value=200.0,  # 显式提供value参数
                chinese_name="迟到数据测试",
                symbol="LATE_TEST",
                category="测试分类",
                current_price=200.0,
                change_percent=0.0,
                source="test_source",
                timestamp=datetime.now()
            )
        ]
        
        # 写入初始数据
        self.writer.write_commodity_data(initial_commodities)
        
        # 创建迟到的数据（1小时前的时间戳）
        import datetime as dt
        one_hour_ago = datetime.now() - dt.timedelta(hours=1)
        
        late_commodities = [
            CommodityData(
                name="Late Data Test",
                value=100.0,  # 显式提供value参数
                chinese_name="迟到数据测试",
                symbol="LATE_TEST",
                category="测试分类",
                current_price=100.0,  # 价格低于当前值
                change_percent=0.0,
                source="test_source",
                timestamp=one_hour_ago
            )
        ]
        
        # 写入迟到数据
        result = self.writer.write_commodity_data(late_commodities)
        self.assertTrue(result)  # 虽然是迟到数据，但写入操作应该成功
        
        # 验证迟到数据是否只写入了历史表，没有更新快照表
        self.writer._connect()
        with self.writer.connection.cursor() as cursor:
            # 检查快照表中的数据是否未更新
            cursor.execute("SELECT current_price FROM commodity_latest WHERE name = %s", 
                          ("Late Data Test",))
            latest_data = cursor.fetchone()
            self.assertEqual(latest_data['current_price'], 200.0)  # 仍然是初始值
            
            # 检查历史表中是否有两条记录
            cursor.execute("SELECT COUNT(*) as count FROM commodity_history WHERE name = %s", 
                          ("Late Data Test",))
            history_count = cursor.fetchone()['count']
            self.assertEqual(history_count, 2)


if __name__ == '__main__':
    unittest.main()