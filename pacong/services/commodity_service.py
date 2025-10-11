"""
商品数据服务
提供高级的商品数据获取和处理功能
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pathlib import Path

from ..core import get_logger, get_config
from ..data import CommodityData, DataProcessor, DataValidator
from ..scrapers import ScraperFactory
from ..output.csv_writer import CSVWriter
from ..output.excel_writer import ExcelWriter
from ..output.mysql_writer import MySQLWriter


class CommodityService:
    """商品数据服务"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.data_processor = DataProcessor()
        self.data_validator = DataValidator()
        
        # 输出目录
        self.output_dir = Path(self.config.output.reports_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.logger.info("商品数据服务初始化完成")
    
    def collect_all_commodity_data(self, scraper_names: Optional[List[str]] = None) -> List[CommodityData]:
        """
        收集所有商品数据
        
        Args:
            scraper_names: 要使用的爬虫名称列表，如果为None则使用所有可用爬虫
            
        Returns:
            List[CommodityData]: 商品数据列表
        """
        self.logger.info("🚀 开始收集商品数据")
        
        # 获取爬虫列表
        if scraper_names is None:
            scraper_names = ScraperFactory.list_available_scrapers()
        
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
        
        self.logger.info(f"📋 总共收集 {len(all_raw_data)} 条原始数据")
        
        # 处理原始数据
        processed_data = self.data_processor.process_raw_data(all_raw_data, "commodity")
        
        # 验证数据
        valid_data, invalid_data = self.data_validator.validate_data_list(processed_data)
        
        # 去重合并
        merged_data = self.data_processor.merge_duplicate_data(valid_data)
        
        self.logger.info(f"🎉 数据收集完成: 有效 {len(merged_data)} 条")
        
        if invalid_data:
            self.logger.warning(f"⚠️ 发现 {len(invalid_data)} 条无效数据")
            validation_summary = self.data_validator.get_validation_summary(invalid_data)
            self.logger.info(f"验证摘要: {validation_summary}")
        
        return merged_data
    
    def get_commodity_by_category(self, commodities: List[CommodityData]) -> Dict[str, List[CommodityData]]:
        """
        按分类分组商品数据
        
        Args:
            commodities: 商品数据列表
            
        Returns:
            Dict[str, List[CommodityData]]: 按分类分组的商品数据
        """
        categories = {}
        
        for commodity in commodities:
            category = commodity.category or "其他"
            if category not in categories:
                categories[category] = []
            categories[category].append(commodity)
        
        # 按价格排序每个分类
        for category in categories:
            categories[category].sort(key=lambda x: x.current_price or 0, reverse=True)
        
        return categories
    
    def get_top_performers(self, commodities: List[CommodityData], limit: int = 10) -> Dict[str, List[CommodityData]]:
        """
        获取表现最佳的商品
        
        Args:
            commodities: 商品数据列表
            limit: 返回数量限制
            
        Returns:
            Dict: 包含涨幅最大和跌幅最大的商品
        """
        # 过滤有变化百分比的商品
        commodities_with_change = [c for c in commodities if c.change_percent is not None]
        
        # 涨幅最大
        top_gainers = sorted(
            commodities_with_change, 
            key=lambda x: x.change_percent, 
            reverse=True
        )[:limit]
        
        # 跌幅最大
        top_losers = sorted(
            commodities_with_change, 
            key=lambda x: x.change_percent
        )[:limit]
        
        return {
            'top_gainers': top_gainers,
            'top_losers': top_losers
        }
    
    def generate_market_summary(self, commodities: List[CommodityData]) -> Dict[str, Any]:
        """
        生成市场摘要
        
        Args:
            commodities: 商品数据列表
            
        Returns:
            Dict: 市场摘要信息
        """
        if not commodities:
            return {"error": "无商品数据"}
        
        # 基本统计
        total_commodities = len(commodities)
        commodities_with_change = [c for c in commodities if c.change_percent is not None]
        
        if commodities_with_change:
            avg_change = sum(c.change_percent for c in commodities_with_change) / len(commodities_with_change)
            gainers = len([c for c in commodities_with_change if c.change_percent > 0])
            losers = len([c for c in commodities_with_change if c.change_percent < 0])
            unchanged = len(commodities_with_change) - gainers - losers
        else:
            avg_change = 0
            gainers = losers = unchanged = 0
        
        # 按分类统计
        categories = self.get_commodity_by_category(commodities)
        category_stats = {}
        
        for category, items in categories.items():
            items_with_change = [c for c in items if c.change_percent is not None]
            if items_with_change:
                cat_avg_change = sum(c.change_percent for c in items_with_change) / len(items_with_change)
            else:
                cat_avg_change = 0
            
            category_stats[category] = {
                'count': len(items),
                'avg_change': round(cat_avg_change, 2)
            }
        
        # 表现最佳
        performers = self.get_top_performers(commodities, 5)
        
        return {
            'summary': {
                'total_commodities': total_commodities,
                'avg_change_percent': round(avg_change, 2),
                'gainers': gainers,
                'losers': losers,
                'unchanged': unchanged,
                'data_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'category_stats': category_stats,
            'top_performers': {
                'top_gainers': [
                    {
                        'name': c.name,
                        'chinese_name': c.chinese_name,
                        'change_percent': c.change_percent,
                        'current_price': c.current_price
                    } for c in performers['top_gainers']
                ],
                'top_losers': [
                    {
                        'name': c.name,
                        'chinese_name': c.chinese_name,
                        'change_percent': c.change_percent,
                        'current_price': c.current_price
                    } for c in performers['top_losers']
                ]
            }
        }
    
    def save_to_csv(self, commodities: List[CommodityData], filename: Optional[str] = None) -> Path:
        """保存为CSV文件"""
        if not filename:
            timestamp = datetime.now().strftime(self.config.output.timestamp_format)
            filename = f"commodity_data_{timestamp}.csv"
        
        filepath = self.output_dir / filename
        
        csv_writer = CSVWriter()
        csv_writer.write_commodity_data(commodities, filepath)
        
        self.logger.info(f"💾 CSV文件已保存: {filepath}")
        return filepath
    
    def save_to_excel(self, commodities: List[CommodityData], filename: Optional[str] = None) -> Path:
        """保存为Excel文件"""
        if not filename:
            timestamp = datetime.now().strftime(self.config.output.timestamp_format)
            filename = f"commodity_data_{timestamp}.xlsx"
        
        filepath = self.output_dir / filename
        
        excel_writer = ExcelWriter()
        excel_writer.write_commodity_data(commodities, filepath)
        
        self.logger.info(f"💾 Excel文件已保存: {filepath}")
        return filepath
    
    def save_to_mysql(self, commodities: List[CommodityData], 
                      host: str = '10.180.248.144', port: int = 3306,
                      user: str = 'root', password: str = 'cJHZQYR7ajrXZd',
                      database: str = 'pacong') -> None:
        """保存数据到MySQL数据库"""
        if not commodities:
            self.logger.warning("无商品数据可写入MySQL")
            return
        
        try:
            mysql_writer = MySQLWriter(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )
            mysql_writer.write_commodity_data(commodities)
            self.logger.info("💾 数据已成功写入MySQL数据库")
        except Exception as e:
            self.logger.error(f"❌ 写入MySQL数据库失败: {e}")
            raise
    
    def run_full_analysis(self, scraper_names: Optional[List[str]] = None, 
                          output_to_file: bool = False) -> Dict[str, Any]:
        """
        运行完整的商品数据分析
        
        Args:
            scraper_names: 要使用的爬虫名称列表
            output_to_file: 是否输出到文件（CSV和Excel）
            
        Returns:
            Dict: 分析结果
        """
        self.logger.info("🎯 开始完整商品数据分析")
        
        # 收集数据
        commodities = self.collect_all_commodity_data(scraper_names)
        
        if not commodities:
            self.logger.error("❌ 未获取到任何商品数据")
            return {"error": "未获取到商品数据"}
        
        # 生成摘要
        summary = self.generate_market_summary(commodities)
        
        # 保存到MySQL数据库
        self.save_to_mysql(commodities)
        
        files = {}
        if output_to_file:
            # 保存文件（如果需要）
            csv_file = self.save_to_csv(commodities)
            excel_file = self.save_to_excel(commodities)
            files = {
                'csv': str(csv_file),
                'excel': str(excel_file)
            }
        
        self.logger.info("✅ 完整分析完成")
        
        return {
            'commodities': commodities,
            'summary': summary,
            'files': files,
            'database': 'MySQL'
        }