"""
外汇数据服务
提供高级的外汇数据获取和处理功能
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from ..core import get_logger, get_config
from ..data import ForexData, DataProcessor, DataValidator
from ..scrapers import ScraperFactory
from ..output.mysql_writer import MySQLWriter


class ForexService:
    """外汇数据服务"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.data_processor = DataProcessor()
        self.data_validator = DataValidator()
        
        self.logger.info("外汇数据服务初始化完成")
    
    def collect_all_forex_data(self, scraper_names: Optional[List[str]] = None) -> List[ForexData]:
        """
        收集所有外汇数据
        
        Args:
            scraper_names: 要使用的爬虫名称列表，如果为None则使用所有可用爬虫
            
        Returns:
            List[ForexData]: 外汇数据列表
        """
        self.logger.info("🚀 开始收集外汇数据")
        
        # 获取爬虫列表
        if scraper_names is None:
            # 获取所有可用爬虫，但我们可能只对特定爬虫感兴趣
            available_scrapers = ScraperFactory.list_available_scrapers()
            # 过滤出可能与外汇相关的爬虫
            scraper_names = [name for name in available_scrapers if name in ['sina_finance']]
            
            if not scraper_names:
                self.logger.warning("⚠️ 未找到外汇相关的爬虫")
                return []
        
        all_raw_data = []
        
        # 使用每个爬虫收集数据
        for scraper_name in scraper_names:
            try:
                self.logger.info(f"📊 使用爬虫: {scraper_name}")
                
                with ScraperFactory.create_scraper(scraper_name) as scraper:
                    if scraper:
                        raw_data = scraper.scrape_all()
                        all_raw_data.extend(raw_data)
                        
                        self.logger.info(f"✅ {scraper_name}: 获取 {len(raw_data)} 条原始数据")
                    else:
                        self.logger.warning(f"⚠️ 无法创建爬虫: {scraper_name}")
                        
            except Exception as e:
                self.logger.error(f"❌ 爬虫 {scraper_name} 执行失败: {e}")
                continue
        
        self.logger.info(f"📋 总共收集 {len(all_raw_data)} 条原始外汇数据")
        
        # 处理原始数据
        processed_data = self.data_processor.process_raw_data(all_raw_data, "forex")
        
        # 验证数据
        valid_data, invalid_data = self.data_validator.validate_data_list(processed_data)
        
        # 去重合并
        merged_data = self.data_processor.merge_duplicate_data(valid_data)
        
        self.logger.info(f"🎉 外汇数据收集完成: 有效 {len(merged_data)} 条")
        
        if invalid_data:
            self.logger.warning(f"⚠️ 发现 {len(invalid_data)} 条无效外汇数据")
            validation_summary = self.data_validator.get_validation_summary(invalid_data)
            self.logger.info(f"验证摘要: {validation_summary}")
        
        return merged_data
    
    def generate_forex_summary(self, forex_data: List[ForexData]) -> Dict[str, Any]:
        """
        生成外汇数据摘要
        
        Args:
            forex_data: 外汇数据列表
            
        Returns:
            Dict: 外汇数据摘要
        """
        if not forex_data:
            return {
                'total_pairs': 0,
                'data_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        # 分类统计
        category_stats = {}
        for data in forex_data:
            category = data.category or '未分类'
            if category not in category_stats:
                category_stats[category] = {
                    'count': 0,
                    'pairs': []
                }
            category_stats[category]['count'] += 1
            category_stats[category]['pairs'].append(data.pair)
        
        # 数据来源统计
        source_stats = {}
        for data in forex_data:
            source = data.source or '未知'
            if source not in source_stats:
                source_stats[source] = 0
            source_stats[source] += 1
        
        return {
            'total_pairs': len(forex_data),
            'category_stats': category_stats,
            'source_stats': source_stats,
            'data_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def save_to_mysql(self, forex_data: List[ForexData], 
                      host: str = 'localhost', 
                      port: int = 3306, 
                      user: str = 'root', 
                      password: str = '123456', 
                      database: str = 'pacong') -> bool:
        """
        将外汇数据保存到MySQL数据库
        
        Args:
            forex_data: 外汇数据列表
            host: 数据库主机地址
            port: 数据库端口
            user: 数据库用户名
            password: 数据库密码
            database: 数据库名称
            
        Returns:
            bool: 是否保存成功
        """
        if not forex_data:
            self.logger.warning("⚠️ 没有可保存的外汇数据")
            return False
        
        try:
            mysql_writer = MySQLWriter(host=host, port=port, user=user, 
                                      password=password, database=database)
            
            # 写入外汇数据
            success = mysql_writer.write_forex_data(forex_data)
            
            if success:
                self.logger.info(f"✅ 成功将 {len(forex_data)} 条外汇数据写入MySQL数据库")
            else:
                self.logger.error("❌ 写入外汇数据到MySQL数据库失败")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ 保存外汇数据到MySQL数据库时发生错误: {e}")
            return False
    
    def run_full_analysis(self, scraper_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        运行完整的外汇数据分析
        
        Args:
            scraper_names: 要使用的爬虫名称列表
            
        Returns:
            Dict: 分析结果
        """
        self.logger.info("🎯 开始完整外汇数据分析")
        
        # 收集数据
        forex_data = self.collect_all_forex_data(scraper_names)
        
        if not forex_data:
            self.logger.error("❌ 未获取到任何外汇数据")
            return {"error": "未获取到外汇数据"}
        
        # 生成摘要
        summary = self.generate_forex_summary(forex_data)
        
        # 保存到MySQL数据库
        save_result = self.save_to_mysql(forex_data)
        
        # 在结果中包含保存状态
        summary['database_save_status'] = 'success' if save_result else 'failed'
        
        self.logger.info("✅ 外汇分析完成")
        
        return summary