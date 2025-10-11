"""
MySQL输出模块
提供将数据写入MySQL数据库的功能，支持快照表、历史表和变更日志
"""

from typing import List, Dict, Any, Optional
import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime
import uuid
import hashlib

from ..core import get_logger
from ..data import CommodityData, ForexData


class MySQLWriter:
    """MySQL数据库写入器，支持快照表、历史表和变更日志"""
    
    def __init__(self, host: str = '10.180.248.144', port: int = 3306, 
                 user: str = 'root', password: str = 'cJHZQYR7ajrXZd', 
                 database: str = 'pacong', charset: str = 'utf8mb4'):
        """
        初始化MySQL写入器
        
        Args:
            host: MySQL主机地址
            port: MySQL端口
            user: MySQL用户名
            password: MySQL密码
            database: MySQL数据库名
            charset: 字符集
        """
        self.logger = get_logger(__name__)
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.charset = charset
        self.connection = None
    
    def _connect(self):
        """建立数据库连接，自动创建数据库（如果不存在）"""
        if not self.connection or not self.connection.open:
            try:
                # 先尝试不指定数据库连接
                self.connection = pymysql.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    charset=self.charset,
                    cursorclass=DictCursor,
                    autocommit=False  # 关闭自动提交，手动管理事务
                )
                
                # 创建数据库（如果不存在）
                with self.connection.cursor() as cursor:
                    create_db_sql = f"CREATE DATABASE IF NOT EXISTS {self.database} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
                    cursor.execute(create_db_sql)
                    self.logger.info(f"数据库 '{self.database}' 已创建或已存在")
                    
                    # 选择数据库
                    cursor.execute(f"USE {self.database};")
                
                self.logger.info(f"成功连接到MySQL数据库: {self.host}:{self.port}/{self.database}")
            except Exception as e:
                self.logger.error(f"连接MySQL数据库失败: {e}")
                raise
    
    def _disconnect(self):
        """关闭数据库连接"""
        if self.connection and self.connection.open:
            self.connection.close()
            self.logger.info("已关闭MySQL数据库连接")
    
    def _create_tables(self):
        """创建必要的表结构：快照表、历史表和变更日志表"""
        try:
            self._connect()
            with self.connection.cursor() as cursor:
                # 创建商品快照表（存放最新数据）
                create_commodity_latest_sql = """
                CREATE TABLE IF NOT EXISTS commodity_latest (
                    id VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    chinese_name VARCHAR(255) NULL,
                    symbol VARCHAR(100) NULL,
                    category VARCHAR(100) NULL,
                    unit VARCHAR(50) NULL,
                    currency VARCHAR(10) NULL DEFAULT 'USD',
                    current_price DECIMAL(18, 8) NULL,
                    open_price DECIMAL(18, 8) NULL,
                    high_price DECIMAL(18, 8) NULL,
                    low_price DECIMAL(18, 8) NULL,
                    previous_close DECIMAL(18, 8) NULL,
                    change_amount DECIMAL(18, 8) NULL,
                    change_percent DECIMAL(18, 8) NULL,
                    volume BIGINT NULL,
                    market_cap DECIMAL(20, 8) NULL,
                    source VARCHAR(255) NULL,
                    version_ts DATETIME NOT NULL,
                    as_of_ts DATETIME NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY idx_name (name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
                cursor.execute(create_commodity_latest_sql)
                
                # 创建商品历史表（存放所有历史数据）
                create_commodity_history_sql = """
                CREATE TABLE IF NOT EXISTS commodity_history (
                    id VARCHAR(64) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    chinese_name VARCHAR(255) NULL,
                    symbol VARCHAR(100) NULL,
                    category VARCHAR(100) NULL,
                    unit VARCHAR(50) NULL,
                    currency VARCHAR(10) NULL DEFAULT 'USD',
                    current_price DECIMAL(18, 8) NULL,
                    open_price DECIMAL(18, 8) NULL,
                    high_price DECIMAL(18, 8) NULL,
                    low_price DECIMAL(18, 8) NULL,
                    previous_close DECIMAL(18, 8) NULL,
                    change_amount DECIMAL(18, 8) NULL,
                    change_percent DECIMAL(18, 8) NULL,
                    volume BIGINT NULL,
                    market_cap DECIMAL(20, 8) NULL,
                    source VARCHAR(255) NULL,
                    version_ts DATETIME NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id, version_ts),
                    INDEX idx_name (name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
                cursor.execute(create_commodity_history_sql)
                
                # 创建变更日志表
                create_change_log_sql = """
                CREATE TABLE IF NOT EXISTS change_log (
                    log_id INT AUTO_INCREMENT PRIMARY KEY,
                    request_id VARCHAR(64) NOT NULL,
                    entity_id VARCHAR(64) NOT NULL,
                    field_name VARCHAR(100) NOT NULL,
                    old_value TEXT NULL,
                    new_value TEXT NULL,
                    version_ts DATETIME NOT NULL,
                    change_type VARCHAR(20) NOT NULL DEFAULT 'UPDATE',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_entity_id (entity_id),
                    INDEX idx_field_name (field_name),
                    INDEX idx_request_id (request_id),
                    INDEX idx_version_ts (version_ts)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
                cursor.execute(create_change_log_sql)
                
            self.connection.commit()
            self.logger.info("成功创建或验证MySQL表结构：快照表、历史表和变更日志表")
        except Exception as e:
            self.logger.error(f"创建MySQL表结构失败: {e}")
            self.connection.rollback()
            raise
    
    def _generate_entity_id(self, name: str, source: str) -> str:
        """\为实体生成唯一ID"""
        # 使用name和source生成唯一ID
        hash_input = f"{name}_{source}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def _get_changed_fields(self, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """\比较新旧数据，返回发生变化的字段"""
        changed_fields = {}
        
        # 定义需要比较的字段
        compare_fields = [
            'name', 'chinese_name', 'symbol', 'category', 'unit', 'currency',
            'current_price', 'open_price', 'high_price', 'low_price', 'previous_close',
            'change_amount', 'change_percent', 'volume', 'market_cap', 'source'
        ]
        
        for field in compare_fields:
            old_value = old_data.get(field) if old_data else None
            new_value = new_data.get(field)
            
            # 处理None值的比较
            if old_value is None and new_value is None:
                continue
            
            # 处理Decimal类型的比较
            if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
                if abs(float(old_value) - float(new_value)) > 0.00000001:  # 精度比较
                    changed_fields[field] = {'old': old_value, 'new': new_value}
            elif old_value != new_value:
                changed_fields[field] = {'old': old_value, 'new': new_value}
        
        return changed_fields
    
    def write_commodity_data(self, commodities: List[CommodityData]):
        """
        写入商品数据到MySQL数据库，实现快照表、历史表和变更日志的管理
        
        Args:
            commodities: 商品数据列表
        """
        if not commodities:
            self.logger.warning("无商品数据可写入MySQL")
            return False
        
        try:
            self._connect()
            self._create_tables()
            
            # 开始事务
            self.connection.begin()
            
            # 生成请求ID
            request_id = str(uuid.uuid4())
            self.logger.info(f"开始处理批量请求: {request_id}, 共 {len(commodities)} 条数据")
            
            # 统计信息
            stats = {
                'total': len(commodities),
                'inserted': 0,
                'updated': 0,
                'skipped': 0,
                'changed_fields': 0
            }
            
            with self.connection.cursor() as cursor:
                for commodity in commodities:
                    # 获取或生成实体ID
                    entity_id = getattr(commodity, 'id', None)
                    if not entity_id:
                        # 如果没有id，使用name和source生成唯一ID
                        entity_id = self._generate_entity_id(commodity.name, commodity.source)
                    
                    # 转换为字典格式
                    commodity_dict = commodity.to_dict() if hasattr(commodity, 'to_dict') else vars(commodity)
                    
                    # 确保version_ts字段存在（数据的真实时间）
                    if 'version_ts' not in commodity_dict or not commodity_dict['version_ts']:
                        commodity_dict['version_ts'] = commodity_dict.get('timestamp', datetime.now())
                    
                    # 锁定并读取旧值（加锁防止并发问题）
                    cursor.execute("SELECT * FROM commodity_latest WHERE id = %s FOR UPDATE", (entity_id,))
                    old_record = cursor.fetchone()
                    
                    # 时间判断 - 处理时间格式和时间先后
                    version_ts = commodity_dict['version_ts']
                    if isinstance(version_ts, str):
                        try:
                            # 尝试解析ISO格式的时间字符串
                            if 'T' in version_ts:
                                version_ts = datetime.fromisoformat(version_ts.replace('Z', '+00:00'))
                            else:
                                version_ts = datetime.strptime(version_ts, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            self.logger.error(f"无法解析时间格式: {version_ts}")
                            if 'failed' not in stats:
                                stats['failed'] = 0
                            stats['failed'] += 1
                            continue
                    
                    # 如果有旧记录，比较时间戳
                    allow_update = True
                    if old_record:
                        as_of_ts = old_record['as_of_ts']  # 快照的更新时间
                        if isinstance(as_of_ts, str):
                            try:
                                as_of_ts = datetime.fromisoformat(as_of_ts.replace('Z', '+00:00')) if 'T' in as_of_ts else \
                                          datetime.strptime(as_of_ts, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                self.logger.error(f"无法解析时间格式: {as_of_ts}")
                                if 'failed' not in stats:
                                    stats['failed'] = 0
                                stats['failed'] += 1
                                continue
                        
                        # 根据用户规则：version_ts更早视为迟到数据，只存档不更新快照
                        if version_ts < as_of_ts:
                            allow_update = False
                            self.logger.warning(f"迟到数据，跳过更新: {commodity.name}, 旧时间: {as_of_ts}, 新时间: {version_ts}")
                            stats['skipped'] += 1
                    
                    # 准备写入历史表的数据
                    history_data = {
                        'id': entity_id,
                        'name': commodity_dict.get('name'),
                        'chinese_name': commodity_dict.get('chinese_name'),
                        'symbol': commodity_dict.get('symbol'),
                        'category': commodity_dict.get('category'),
                        'unit': commodity_dict.get('unit'),
                        'currency': commodity_dict.get('currency', 'USD'),
                        'current_price': commodity_dict.get('current_price'),
                        'open_price': commodity_dict.get('open_price'),
                        'high_price': commodity_dict.get('high_price'),
                        'low_price': commodity_dict.get('low_price'),
                        'previous_close': commodity_dict.get('previous_close'),
                        'change_amount': commodity_dict.get('change_amount'),
                        'change_percent': commodity_dict.get('change_percent'),
                        'volume': commodity_dict.get('volume'),
                        'market_cap': commodity_dict.get('market_cap'),
                        'source': commodity_dict.get('source'),
                        'version_ts': version_ts
                    }
                    
                    # 写历史存档（无论有没有更新快照，都向历史表追加一行）
                    insert_history_sql = """
                    INSERT IGNORE INTO commodity_history (
                        id, name, chinese_name, symbol, category, unit, currency,
                        current_price, open_price, high_price, low_price, previous_close,
                        change_amount, change_percent, volume, market_cap, source, version_ts
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_history_sql, (
                        history_data['id'], history_data['name'], history_data['chinese_name'],
                        history_data['symbol'], history_data['category'], history_data['unit'],
                        history_data['currency'], history_data['current_price'], history_data['open_price'],
                        history_data['high_price'], history_data['low_price'], history_data['previous_close'],
                        history_data['change_amount'], history_data['change_percent'], history_data['volume'],
                        history_data['market_cap'], history_data['source'], history_data['version_ts']
                    ))
                    
                    # 如果是迟到数据，跳过快照表更新和变更日志记录
                    if not allow_update:
                        continue
                    
                    # 列对比 - 只挑出值发生变化的列
                    changed_fields = self._get_changed_fields(old_record, history_data)
                    
                    # 如果没有变化，跳过更新
                    if not changed_fields and old_record:
                        stats['skipped'] += 1
                        continue
                    
                    # 更新最新快照（精确UPDATE）
                    if old_record:
                        # 有旧记录，执行UPDATE
                        if changed_fields:
                            # 构建UPDATE语句 - 仅对发生变化的列做UPDATE
                            set_clause = ", ".join([f"{field} = %s" for field in changed_fields.keys()])
                            set_clause += ", as_of_ts = %s, version_ts = %s"  # 更新快照的更新时间和数据时间
                            
                            # 准备参数
                            params = list(changed_fields[field]['new'] for field in changed_fields.keys())
                            params.append(version_ts)
                            params.append(version_ts)
                            params.append(entity_id)
                            
                            update_sql = f"UPDATE commodity_latest SET {set_clause} WHERE id = %s"
                            cursor.execute(update_sql, params)
                            stats['updated'] += 1
                            
                            # 记录变更日志 - 对变化的列逐列插入change_log
                            for field, values in changed_fields.items():
                                insert_change_log_sql = """
                                INSERT INTO change_log (
                                    request_id, entity_id, field_name, old_value, new_value, version_ts
                                ) VALUES (%s, %s, %s, %s, %s, %s)
                                """
                                # 处理可能的None值
                                old_val = str(values['old']) if values['old'] is not None else None
                                new_val = str(values['new']) if values['new'] is not None else None
                                
                                cursor.execute(insert_change_log_sql, (
                                    request_id, entity_id, field, old_val, new_val, version_ts
                                ))
                                stats['changed_fields'] += 1
                    else:
                        # 没有旧记录，执行INSERT并写as_of_ts
                        insert_latest_sql = """
                        INSERT INTO commodity_latest (
                            id, name, chinese_name, symbol, category, unit, currency,
                            current_price, open_price, high_price, low_price, previous_close,
                            change_amount, change_percent, volume, market_cap, source, version_ts, as_of_ts
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(insert_latest_sql, (
                            history_data['id'], history_data['name'], history_data['chinese_name'],
                            history_data['symbol'], history_data['category'], history_data['unit'],
                            history_data['currency'], history_data['current_price'], history_data['open_price'],
                            history_data['high_price'], history_data['low_price'], history_data['previous_close'],
                            history_data['change_amount'], history_data['change_percent'], history_data['volume'],
                            history_data['market_cap'], history_data['source'], history_data['version_ts'],
                            history_data['version_ts']  # as_of_ts设为version_ts
                        ))
                        stats['inserted'] += 1
                        
                        # 记录插入类型的变更日志
                        insert_change_log_sql = """
                        INSERT INTO change_log (
                            request_id, entity_id, field_name, new_value, version_ts, change_type
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(insert_change_log_sql, (
                            request_id, entity_id, 'record', f'New record created: {history_data["name"]}', 
                            version_ts, 'INSERT'
                        ))
                        stats['changed_fields'] += 1
                
            # 提交事务 - 三件事同事务提交：快照更新、历史追加、变更日志
            self.connection.commit()
            
            # 输出运行日志
            self.logger.info(
                f"批量请求处理完成: {request_id}\n" \
                f"总计: {stats['total']}, 插入: {stats['inserted']}, 更新: {stats['updated']}, 跳过: {stats['skipped']}\n" \
                f"变更字段数: {stats.get('changed_fields', 0)}"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"写入MySQL商品数据失败: {e}")
            if self.connection and self.connection.open:
                self.connection.rollback()
            raise
        finally:
            self._disconnect()
    
    def write_forex_data(self, forex_data: List[ForexData]):
        """
        写入外汇数据到MySQL数据库
        
        Args:
            forex_data: 外汇数据列表
        """
        # 简化版实现，保持原有功能
        if not forex_data:
            self.logger.warning("无外汇数据可写入MySQL")
            return False
        
        try:
            self._connect()
            # 为了兼容性，创建旧的forex_data表
            with self.connection.cursor() as cursor:
                create_forex_table_sql = """
                CREATE TABLE IF NOT EXISTS forex_data (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    base_currency VARCHAR(10) NULL,
                    quote_currency VARCHAR(10) NULL,
                    pair VARCHAR(20) NULL,
                    bid_price DECIMAL(18, 8) NULL,
                    ask_price DECIMAL(18, 8) NULL,
                    mid_price DECIMAL(18, 8) NULL,
                    change_amount DECIMAL(18, 8) NULL,
                    change_percent DECIMAL(18, 8) NULL,
                    spread DECIMAL(18, 8) NULL,
                    source VARCHAR(255) NULL,
                    timestamp DATETIME NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_forex (pair, source, timestamp)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
                cursor.execute(create_forex_table_sql)
                self.connection.commit()
            
            with self.connection.cursor() as cursor:
                # 批量插入外汇数据
                insert_sql = """
                INSERT IGNORE INTO forex_data (
                    name, base_currency, quote_currency, pair,
                    bid_price, ask_price, mid_price,
                    change_amount, change_percent, spread,
                    source, timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                data_to_insert = []
                for forex in forex_data:
                    data_to_insert.append((
                        forex.name,
                        forex.base_currency,
                        forex.quote_currency,
                        forex.pair,
                        forex.bid_price,
                        forex.ask_price,
                        forex.mid_price,
                        forex.change_amount,
                        forex.change_percent,
                        forex.spread,
                        forex.source,
                        forex.timestamp
                    ))
                
                # 批量执行插入
                cursor.executemany(insert_sql, data_to_insert)
                self.connection.commit()
                
                self.logger.info(f"成功写入 {len(forex_data)} 条外汇数据到MySQL数据库")
                
            return True
            
        except Exception as e:
            self.logger.error(f"写入MySQL外汇数据失败: {e}")
            if self.connection and self.connection.open:
                self.connection.rollback()
            raise
        finally:
            self._disconnect()


# 测试函数
def test_mysql_writer():
    """测试MySQL写入器是否正常工作"""
    try:
        from ..data.models import CommodityData
        from datetime import datetime
        import random
        
        # 创建测试数据
        test_commodities = [
            CommodityData(
                name=f"Test Commodity {i}",
                chinese_name=f"测试商品 {i}",
                symbol=f"TEST{i}",
                category="测试分类",
                current_price=random.uniform(10, 1000),
                change_percent=random.uniform(-5, 5),
                source="test_source",
                timestamp=datetime.now()
            ) for i in range(3)
        ]
        
        # 初始化写入器，使用配置的数据库连接信息
        writer = MySQLWriter(
            host='10.180.248.144',
            port=3306,
            user='root',
            password='cJHZQYR7ajrXZd',
            database='pacong'
        )
        
        # 写入测试数据
        result = writer.write_commodity_data(test_commodities)
        
        print(f"MySQL写入测试{'成功' if result else '失败'}!")
        return result
    except Exception as e:
        print(f"MySQL写入测试失败: {e}")
        return False


if __name__ == "__main__":
    test_mysql_writer()