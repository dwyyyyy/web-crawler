"""
新浪财经外盘期货数据爬虫
使用新浪API获取外盘期货数据
"""

import re
import json
import requests
from typing import List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup

from ..core import BaseScraper, WebScrapingMixin, get_config
from ..data import CommodityData


class SinaForexFuturesScraper(BaseScraper, WebScrapingMixin):
    """新浪财经外盘期货数据爬虫"""
    
    def __init__(self, **kwargs):
        super().__init__("sina_forex_futures", **kwargs)
        self.base_url = "https://finance.sina.com.cn/money/future/hf.html"
        self.logger.info("初始化爬虫: sina_forex_futures")
        
        # 外盘期货代码映射表 - 从页面JavaScript中提取的完整映射
        self.futures_codes = {
            "NAS": ["纳指期货", 0],
            "ES": ["标普期货", 0],
            "DJS": ["道指期货", 0],
            "CT": ["NYBOT-棉花", 22.0462, "美分/磅"],
            "NID": ["LME镍3个月", 1, "美元/吨"],
            "PBD": ["LME铅3个月", 1, "美元/吨"],
            "SND": ["LME锡3个月", 1, "美元/吨"],
            "ZSD": ["LME锌3个月", 1, "美元/吨"],
            "AHD": ["LME铝3个月", 1, "美元/吨"],
            "CAD": ["LME铜3个月", 1, "美元/吨"],
            "S": ["CBOT-黄豆", 0.367437, "美分/蒲式耳"],
            "W": ["CBOT-小麦", 0.367437, "美分/蒲式耳"],
            "C": ["CBOT-玉米", 0.3936825, "美分/蒲式耳"],
            "BO": ["CBOT-黄豆油", 22.0462, "美分/磅"],
            "SM": ["CBOT-黄豆粉", 1.1025, "美元/短吨"],
            "TAL": ["日本铝", 0, "美元/吨"],
            "TRB": ["日本橡胶", 1000, "日元/公斤", "jpy"],
            "HG": ["COMEX铜", 22.0462, "美分/磅"],
            "NG": ["NYMEX天然气", 0],
            "CL": ["NYMEX原油", 7.3, "美元/桶"],
            "SI": ["COMEX白银", 0],
            "GC": ["COMEX黄金", 0.03215, "美元/盎司"],
            "DXF": ["美元指数期货", 0],
            "SF": ["IMM-瑞郎", 0],
            "CD": ["IMM-加元", 0],
            "JY": ["IMM-日元", 0],
            "BP": ["IMM-英镑", 0],
            "EC": ["IMM-欧元", 0]
        }
    
    def get_data_sources(self) -> List[Dict[str, str]]:
        """获取数据源列表"""
        config = get_config()
        sina_config = config.data_sources.get('sina_forex_futures', {})
        
        if not sina_config.get('enabled', True):
            return []
        
        return [{
            'name': '新浪财经外盘期货',
            'url': self.base_url,
            'type': 'commodity'
        }]
    
    def scrape_single_source(self, source: Dict[str, str]) -> List[Dict[str, Any]]:
        """爬取单个数据源"""
        self.logger.info(f"开始爬取新浪财经外盘期货: {source['url']}")
        
        try:
            # 构建API URL - 按照页面JavaScript中的格式构建
            futures_codes_str = ",".join([f"hf_{code}" for code in self.futures_codes.keys()])
            api_url = f"http://hq.sinajs.cn/?list={futures_codes_str}"
            
            # 获取汇率数据用于换算
            exchange_url = "http://hq.sinajs.cn/?list=USDCNY,JPY"
            
            # 使用自定义请求头来模拟浏览器行为
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": "https://finance.sina.com.cn/money/future/hf.html",
                "Host": "hq.sinajs.cn",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
                "Connection": "keep-alive"
            }
            
            # 获取数据 - 使用自定义请求头
            futures_data = self._get_futures_data(api_url, headers)
            exchange_rates = self._get_exchange_rates(exchange_url, headers)
            
            # 解析和处理数据
            result = self._parse_and_process_data(futures_data, exchange_rates)
            
            self.logger.info(f"成功提取 {len(result)} 条外盘期货数据")
            return result
            
        except Exception as e:
            self.logger.error(f"爬取新浪财经外盘期货失败: {e}")
            return []
    
    def _parse_and_process_data(self, futures_data: Dict[str, List[str]], exchange_rates: Dict[str, float]) -> List[Dict[str, Any]]:
        """解析和处理数据"""
        result = []
        
        for code, values in futures_data.items():
            if code in self.futures_codes and len(values) >= 10:
                # 提取基本数据
                try:
                    name_info = self.futures_codes[code]
                    name = name_info[0]
                    
                    # 解析数据 - 添加更多的检查来避免空值
                    latest_price = float(values[0]) if values[0] and values[0] != '-' and values[0] != 'NoData.' else 0.0
                    open_price = float(values[1]) if values[1] and values[1] != '-' and values[1] != 'NoData.' else 0.0
                    high_price = float(values[2]) if values[2] and values[2] != '-' and values[2] != 'NoData.' else 0.0
                    low_price = float(values[3]) if values[3] and values[3] != '-' and values[3] != 'NoData.' else 0.0
                    prev_close = float(values[7]) if values[7] and values[7] != '-' and values[7] != 'NoData.' else 0.0
                    
                    # 计算涨跌幅
                    change = latest_price - prev_close
                    change_percent = (change / prev_close * 100) if prev_close != 0 else 0.0
                    
                    # 构建数据字典
                    data = {
                        'name': name,
                        'code': code,
                        'latest_price': latest_price,
                        'open_price': open_price,
                        'high_price': high_price,
                        'low_price': low_price,
                        'prev_close': prev_close,
                        'change': change,
                        'change_percent': change_percent,
                        'source': 'sina_forex_futures',
                        'timestamp': datetime.now()
                    }
                    
                    # 如果有换算因子，计算人民币价格
                    if len(name_info) > 1 and name_info[1] != 0:
                        # 确定使用哪种汇率
                        if len(name_info) > 3 and name_info[3] == 'jpy':
                            rate = exchange_rates['jpy_cny']
                        else:
                            rate = exchange_rates['usd_cny']
                        
                        # 计算人民币价格
                        cny_price = latest_price * name_info[1] * rate
                        data['current_price'] = round(cny_price, 2)
                        data['unit'] = '元/吨' if '吨' in name else '元'
                    else:
                        data['current_price'] = latest_price
                        data['unit'] = name_info[2] if len(name_info) > 2 else ''
                    
                    # 验证数据
                    if self.validate_data(data):
                        result.append(data)
                except Exception as e:
                    self.logger.warning(f"解析期货数据失败 ({code}): {e}")
                    continue
        
        return result
    def _extract_data_from_html(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """从HTML中提取数据 - 备用方案"""
        self.logger.warning("_extract_data_from_html方法已废弃，请使用主要API方法")
        return []
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """验证单条数据的有效性"""
        # 检查必需字段
        required_fields = ['name', 'current_price', 'latest_price']
        for field in required_fields:
            if field not in data or data[field] is None:
                self.logger.warning(f"数据缺少必需字段: {field}")
                return False
        
        # 检查价格是否为有效数字
        try:
            current_price = float(data['current_price'])
            latest_price = float(data['latest_price'])
            
            # 价格不能为负数或0（除非是特殊情况）
            if current_price <= 0 and latest_price <= 0:
                self.logger.warning(f"价格无效: {data['name']} - {current_price}")
                return False
            
        except (ValueError, TypeError):
            self.logger.warning(f"价格格式错误: {data['name']}")
            return False
        
        return True
    
    def clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗单条数据"""
        cleaned_data = super().clean_data(data)
        
        # 确保所有数值字段都是浮点数
        numeric_fields = ['current_price', 'latest_price', 'open_price', 'high_price', 'low_price', 'prev_close', 'change', 'change_percent']
        for field in numeric_fields:
            if field in cleaned_data and cleaned_data[field] is not None:
                try:
                    cleaned_data[field] = float(cleaned_data[field])
                except (ValueError, TypeError):
                    cleaned_data[field] = 0.0
        
        # 规范化商品名称
        if 'name' in cleaned_data:
            # 移除可能的代码前缀
            cleaned_data['name'] = cleaned_data['name'].replace('NYBOT-', '').replace('LME-', '').replace('CBOT-', '').replace('NYMEX-', '').replace('COMEX-', '').replace('IMM-', '')
        
        # 确保时间戳格式正确
        if 'timestamp' in cleaned_data and not isinstance(cleaned_data['timestamp'], datetime):
            try:
                cleaned_data['timestamp'] = datetime.now()
            except:
                pass
        
        return cleaned_data
        
    def _get_futures_data(self, api_url: str, headers: Dict[str, str]) -> Dict[str, List[str]]:
        """从新浪财经API获取外盘期货数据"""
        result = {}
        try:
            # 发送请求，设置超时时间
            response = requests.get(api_url, headers=headers, timeout=10)
            
            # 检查响应状态
            if response.status_code != 200:
                self.logger.error(f"新浪财经API请求失败 (状态码: {response.status_code})")
                return result
            
            # 解析响应内容
            content = response.text
            
            # 使用正则表达式提取数据
            pattern = r'var hq_str_hf_([^=]+)="([^"]*)"'
            matches = re.finditer(pattern, content)
            
            for match in matches:
                code = match.group(1)
                values_str = match.group(2)
                values = values_str.split(',') if values_str else []
                
                # 存储提取的数据
                result[code] = values
                
        except requests.RequestException as e:
            self.logger.error(f"新浪财经API请求异常: {e}")
        except Exception as e:
            self.logger.error(f"解析新浪财经API数据失败: {e}")
        
        return result
        
    def _get_exchange_rates(self, exchange_url: str, headers: Dict[str, str]) -> Dict[str, float]:
        """获取汇率数据用于价格换算"""
        # 默认汇率（以防API请求失败）
        rates = {
            'usd_cny': 7.0,
            'jpy_cny': 0.05
        }
        
        try:
            # 发送请求，设置超时时间
            response = requests.get(exchange_url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                content = response.text
                
                # 提取美元/人民币汇率
                usd_pattern = r'var hq_str_USDCNY="([^"]*)"'
                usd_match = re.search(usd_pattern, content)
                if usd_match:
                    usd_values = usd_match.group(1).split(',')
                    # 美元/人民币汇率通常在第2个位置
                    if len(usd_values) >= 2 and usd_values[1]:
                        try:
                            rates['usd_cny'] = float(usd_values[1])
                        except ValueError:
                            self.logger.warning(f"解析美元/人民币汇率失败: {usd_values[1]}")
                
                # 提取日元/人民币汇率
                jpy_pattern = r'var hq_str_JPY="([^"]*)"'
                jpy_match = re.search(jpy_pattern, content)
                if jpy_match:
                    jpy_values = jpy_match.group(1).split(',')
                    # 日元/人民币汇率通常在第2个位置
                    if len(jpy_values) >= 2 and jpy_values[1]:
                        try:
                            # 注意：日元汇率通常是100日元兑人民币
                            rates['jpy_cny'] = float(jpy_values[1]) / 100
                        except ValueError:
                            self.logger.warning(f"解析日元/人民币汇率失败: {jpy_values[1]}")
                
            else:
                self.logger.warning(f"汇率API请求失败 (状态码: {response.status_code})")
                
        except requests.RequestException as e:
            self.logger.warning(f"汇率API请求异常: {e}")
        except Exception as e:
            self.logger.warning(f"解析汇率数据失败: {e}")
        
        return rates