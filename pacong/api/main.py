"""
FastAPI主应用文件
提供商品数据的RESTful API接口
"""
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..core import get_logger
from ..data.models import CommodityData
from ..output.mysql_writer import MySQLWriter

import json
from fastapi.responses import JSONResponse

# 自定义JSON响应类，确保中文正确显示
class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"

# 创建FastAPI应用
app = FastAPI(
    title="商品数据API",
    description="提供商品数据的查询接口",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "基础接口",
            "description": "API基本功能接口"
        },
        {
            "name": "商品价格接口",
            "description": "商品价格查询相关接口"
        }
    ],
    default_response_class=UTF8JSONResponse
)

# 添加CORS支持
origins = [
    "*",  # 生产环境应该限制为特定域名
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = get_logger(__name__)

class MySQLReader(MySQLWriter):
    """MySQL数据库读取器，扩展MySQLWriter提供读取数据的功能"""
    
    def get_latest_price(self, commodity_name: str) -> Dict[str, Any]:
        """
        获取指定商品的最新价格和涨跌幅
        
        Args:
            commodity_name: 商品名称
        
        Returns:
            Dict: 包含商品最新价格和涨跌幅的数据
        
        Raises:
            Exception: 当数据库操作失败时抛出异常
        """
        try:
            self._connect()
            with self.connection.cursor() as cursor:
                sql = """
                SELECT name, chinese_name, current_price, change_amount, change_percent, 
                       currency, source, version_ts 
                FROM commodity_latest 
                WHERE name = %s
                """
                cursor.execute(sql, (commodity_name,))
                result = cursor.fetchone()
                
                if not result:
                    logger.warning(f"未找到商品 '{commodity_name}' 的最新价格数据")
                    return None
                
                # 格式化时间戳
                if 'version_ts' in result and isinstance(result['version_ts'], datetime):
                    result['version_ts'] = result['version_ts'].isoformat()
                
                return result
        except pymysql.MySQLError as e:
            logger.error(f"MySQL数据库错误 - 获取最新价格: {e}")
            raise
        except Exception as e:
            logger.error(f"获取最新价格数据失败: {e}")
            raise
        finally:
            self._disconnect()
    
    def get_price_history(self, commodity_name: str, start_time: datetime, end_time: datetime = None) -> List[Dict[str, Any]]:
        """
        获取指定商品在某时间段的价格历史
        
        Args:
            commodity_name: 商品名称
            start_time: 开始时间
            end_time: 结束时间（默认为当前时间）
        
        Returns:
            List[Dict]: 包含历史价格数据的列表
        
        Raises:
            Exception: 当数据库操作失败时抛出异常
        """
        try:
            self._connect()
            
            if end_time is None:
                end_time = datetime.now()
            
            with self.connection.cursor() as cursor:
                sql = """
                SELECT name, current_price, created_at 
                FROM commodity_history 
                WHERE name = %s AND created_at BETWEEN %s AND %s
                ORDER BY created_at DESC
                """
                cursor.execute(sql, (commodity_name, start_time, end_time))
                results = cursor.fetchall()
                
                # 格式化时间戳
                for result in results:
                    if 'created_at' in result and isinstance(result['created_at'], datetime):
                        result['created_at'] = result['created_at'].isoformat()
                
                return results
        except pymysql.MySQLError as e:
            logger.error(f"MySQL数据库错误 - 获取历史价格: {e}")
            raise
        except Exception as e:
            logger.error(f"获取历史价格数据失败: {e}")
            raise
        finally:
            self._disconnect()
    
    def get_price_changes(self, commodity_name: Optional[str] = None, start_time: Optional[datetime] = None, 
                         end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        查询历史表中商品的价格、涨跌幅和创建时间
        
        Args:
            commodity_name: 商品名称
            start_time: 开始时间
            end_time: 结束时间
        
        Returns:
            List[Dict]: 包含商品价格、涨跌幅和创建时间的数据
        
        Raises:
            Exception: 当数据库操作失败时抛出异常
        """
        try:
            self._connect()
            
            if end_time is None:
                end_time = datetime.now()
            
            with self.connection.cursor() as cursor:
                # 构建查询条件
                conditions = []
                params = []
                
                if commodity_name:
                    conditions.append("name = %s")
                    params.append(commodity_name)
                
                if start_time:
                    conditions.append("created_at >= %s")
                    params.append(start_time)
                
                if end_time:
                    conditions.append("created_at <= %s")
                    params.append(end_time)
                
                # 如果没有条件，默认查询最近24小时的数据
                if not conditions:
                    conditions.append("created_at >= %s")
                    params.append(datetime.now() - timedelta(days=1))
                
                # 构建SQL查询
                where_clause = " AND ".join(conditions)
                sql = f"""
                SELECT name, current_price, change_percent, created_at
                FROM commodity_history
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT 1000
                """
                
                cursor.execute(sql, tuple(params))
                results = cursor.fetchall()
                
                # 格式化时间戳
                for result in results:
                    if 'created_at' in result and isinstance(result['created_at'], datetime):
                        result['created_at'] = result['created_at'].isoformat()
                
                return results
        except pymysql.MySQLError as e:
            logger.error(f"MySQL数据库错误 - 获取价格变化: {e}")
            raise
        except Exception as e:
            logger.error(f"获取价格变化记录失败: {e}")
            raise
        finally:
            self._disconnect()

# 初始化数据库读取器
db_reader = MySQLReader(
    host='10.180.248.144',
    port=3306,
    user='root',
    password='cJHZQYR7ajrXZd',
    database='pacong'
)

@app.get("/", summary="API根路径", tags=["基础接口"])
async def root():
    """API根路径，返回欢迎信息"""
    import json
    from fastapi.responses import JSONResponse
    
    data = {
        "message": "欢迎使用商品数据API",
        "version": "1.0.0",
        "endpoints": [
            "/api/latest-price?name=商品名称",
            "/api/price-history?name=商品名称&start_time=2023-01-01T00:00:00",
            "/api/price-changes"
        ],
        "docs": "http://localhost:8000/docs"
    }
    
    return JSONResponse(content=data, media_type="application/json; charset=utf-8")

@app.get("/api/latest-price", summary="查询最新价格", tags=["商品价格接口"])
async def get_latest_price(
    name: str = Query(..., description="商品名称，例如：玉米")
):
    """
    查询指定商品的最新价格
    
    - **name**: 商品名称，例如：玉米
    - **返回**: 包含当前价格和版本时间戳的JSON对象
    """
    try:
        result = db_reader.get_latest_price(name)
        if not result:
            raise HTTPException(status_code=404, detail=f"未找到商品 '{name}' 的最新价格数据")
        # 返回价格和版本时间戳字段
        return {"price": result["current_price"], "version_ts": result["version_ts"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询最新价格接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@app.get("/api/price-history", summary="查询历史数据", tags=["商品价格接口"])
async def get_price_history(
    name: str = Query(..., description="商品名称，例如：玉米"),
    start_time: datetime = Query(..., description="开始时间，格式：YYYY-MM-DDTHH:MM:SS"),
    end_time: Optional[datetime] = Query(None, description="结束时间，格式：YYYY-MM-DDTHH:MM:SS")
):
    """
    查询指定商品在某时间段的价格历史
    
    - **name**: 商品名称，例如：玉米
    - **start_time**: 开始时间，格式：YYYY-MM-DDTHH:MM:SS
    - **end_time**: 结束时间（可选），格式：YYYY-MM-DDTHH:MM:SS
    - **返回**: 包含历史价格数据的列表
    """
    try:
        results = db_reader.get_price_history(name, start_time, end_time)
        # 只保留创建时间和价格数据
        simplified_results = [
            {
                "create_time": item["created_at"],
                "price": item["current_price"]
            } 
            for item in results
        ]
        return simplified_results
    except Exception as e:
        logger.error(f"查询历史价格接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@app.get("/api/price-changes", summary="查询历史价格数据变化", tags=["商品价格接口"])
async def get_price_changes(
    name: Optional[str] = Query(None, description="商品名称，例如：玉米"),
    start_time: Optional[datetime] = Query(None, description="开始时间，格式：YYYY-MM-DDTHH:MM:SS"),
    end_time: Optional[datetime] = Query(None, description="结束时间，格式：YYYY-MM-DDTHH:MM:SS")
):
    """
    查询历史表中商品的价格和创建时间，并计算每条记录（除第一条外）与其上一条记录之间的价格变化百分比
    
    - **name**: 商品名称（可选），例如：玉米
    - **start_time**: 开始时间（可选），格式：YYYY-MM-DDTHH:MM:SS
    - **end_time**: 结束时间（可选），格式：YYYY-MM-DDTHH:MM:SS
    - **返回**: 包含商品价格、计算的价格变化百分比和创建时间的数据列表
    - **说明**: 如果不指定任何参数，默认查询最近24小时的所有商品数据
    """
    try:
        # 获取原始数据
        results = db_reader.get_price_changes(commodity_name=name, start_time=start_time, end_time=end_time)
        
        # 如果没有结果，直接返回
        if not results:
            return {
                "name": name,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "data_count": 0,
                "data": []
            }
        
        # 首先按照创建时间升序排列数据，以便正确计算相邻记录间的变化
        # 从数据库返回的数据已经是ISO格式的字符串，需要转回datetime对象进行排序
        sorted_results = sorted(results, key=lambda x: datetime.fromisoformat(x['created_at']))
        
        # 准备处理后的数据列表
        processed_data = []
        
        # 遍历排序后的结果，计算相邻记录间的价格变化百分比
        for i, record in enumerate(sorted_results):
            # 创建处理后的记录，不包含原始的change_percent
            processed_record = {
                "name": record["name"],
                "current_price": record["current_price"],
                "created_at": record["created_at"]
            }
            
            # 对于第一条记录（最早的记录），没有前一条记录可以比较，所以不计算变化百分比
            if i > 0:
                # 获取前一条记录（更早的记录）
                prev_record = sorted_results[i-1]
                # 计算价格变化百分比：(当前价格 - 前一条价格) / 前一条价格 * 100
                if prev_record["current_price"] != 0:  # 避免除以零
                    price_change_percent = ((record["current_price"] - prev_record["current_price"]) / prev_record["current_price"]) * 100
                    processed_record["calculated_change_percent"] = round(price_change_percent, 6)  # 保留六位小数，以便显示微小变化
                else:
                    processed_record["calculated_change_percent"] = None  # 无法计算
            
            processed_data.append(processed_record)
        
        # 按照创建时间降序返回（最新的记录在前），满足接口二按时间倒序的要求
        processed_data.sort(key=lambda x: datetime.fromisoformat(x['created_at']), reverse=True)
        
        return {
            "name": name,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "data_count": len(processed_data),
            "data": processed_data
        }
    except Exception as e:
        logger.error(f"查询历史价格数据接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)