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
    """MySQL数据库读取器，扩展MySQLWriter"""
    
    def get_latest_price(self, commodity_name: str) -> Dict[str, Any]:
        """
        获取指定商品的最新价格和涨跌幅
        
        Args:
            commodity_name: 商品名称
        
        Returns:
            Dict: 包含商品最新价格和涨跌幅的数据
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
        """
        try:
            self._connect()
            
            if end_time is None:
                end_time = datetime.now()
            
            with self.connection.cursor() as cursor:
                sql = """
                SELECT name, current_price, change_percent, version_ts 
                FROM commodity_history 
                WHERE name = %s AND version_ts BETWEEN %s AND %s
                ORDER BY version_ts ASC
                """
                cursor.execute(sql, (commodity_name, start_time, end_time))
                results = cursor.fetchall()
                
                # 格式化时间戳
                for result in results:
                    if 'version_ts' in result and isinstance(result['version_ts'], datetime):
                        result['version_ts'] = result['version_ts'].isoformat()
                
                return results
        except Exception as e:
            logger.error(f"获取历史价格数据失败: {e}")
            raise
        finally:
            self._disconnect()
    
    def get_price_changes(self, request_id: Optional[str] = None, start_time: Optional[datetime] = None, 
                         end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        查看某次抓取或某时间段的价格变化
        
        Args:
            request_id: 请求ID（某次抓取的标识）
            start_time: 开始时间
            end_time: 结束时间
        
        Returns:
            List[Dict]: 包含价格变化记录的数据
        """
        try:
            self._connect()
            
            with self.connection.cursor() as cursor:
                # 构建查询条件
                conditions = []
                params = []
                
                if request_id:
                    conditions.append("log.request_id = %s")
                    params.append(request_id)
                
                if start_time:
                    conditions.append("log.version_ts >= %s")
                    params.append(start_time)
                
                if end_time:
                    conditions.append("log.version_ts <= %s")
                    params.append(end_time)
                
                # 如果没有条件，默认查询最近24小时的数据
                if not conditions:
                    conditions.append("log.version_ts >= %s")
                    params.append(datetime.now() - timedelta(days=1))
                
                # 构建SQL查询
                where_clause = " AND ".join(conditions)
                sql = f"""
                SELECT cl.name, cl.chinese_name, cl.currency, 
                       cl.current_price, cl.change_percent, cl.version_ts,
                       cl.source, cl.id as entity_id,
                       log.request_id, log.field_name, log.old_value, log.new_value, log.change_type
                FROM change_log log
                JOIN commodity_latest cl ON log.entity_id = cl.id
                WHERE {where_clause}
                ORDER BY log.version_ts DESC, log.log_id DESC
                LIMIT 1000
                """
                
                cursor.execute(sql, tuple(params))
                results = cursor.fetchall()
                
                # 格式化时间戳
                for result in results:
                    if 'version_ts' in result and isinstance(result['version_ts'], datetime):
                        result['version_ts'] = result['version_ts'].isoformat()
                
                return results
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
    name: str = Query(..., description="商品名称，例如：黄金期货主力合约")
):
    """
    查询指定商品的最新价格和涨跌幅
    
    - **name**: 商品名称，例如：黄金期货主力合约
    - **返回**: 包含商品名称、当前价格、涨跌幅等信息的JSON对象
    """
    try:
        result = db_reader.get_latest_price(name)
        if not result:
            raise HTTPException(status_code=404, detail=f"未找到商品 '{name}' 的最新价格数据")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询最新价格接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@app.get("/api/price-history", summary="查询历史数据", tags=["商品价格接口"])
async def get_price_history(
    name: str = Query(..., description="商品名称，例如：黄金期货主力合约"),
    start_time: datetime = Query(..., description="开始时间，格式：YYYY-MM-DDTHH:MM:SS"),
    end_time: Optional[datetime] = Query(None, description="结束时间，格式：YYYY-MM-DDTHH:MM:SS")
):
    """
    查询指定商品在某时间段的价格历史
    
    - **name**: 商品名称，例如：黄金期货主力合约
    - **start_time**: 开始时间，格式：YYYY-MM-DDTHH:MM:SS
    - **end_time**: 结束时间（可选），格式：YYYY-MM-DDTHH:MM:SS
    - **返回**: 包含历史价格数据的列表
    """
    try:
        results = db_reader.get_price_history(name, start_time, end_time)
        return {
            "name": name,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat() if end_time else datetime.now().isoformat(),
            "data_count": len(results),
            "data": results
        }
    except Exception as e:
        logger.error(f"查询历史价格接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@app.get("/api/price-changes", summary="查询变更记录", tags=["商品价格接口"])
async def get_price_changes(
    request_id: Optional[str] = Query(None, description="请求ID（某次抓取的标识）"),
    start_time: Optional[datetime] = Query(None, description="开始时间，格式：YYYY-MM-DDTHH:MM:SS"),
    end_time: Optional[datetime] = Query(None, description="结束时间，格式：YYYY-MM-DDTHH:MM:SS")
):
    """
    查看某次抓取或某时间段的价格变化
    
    - **request_id**: 请求ID（某次抓取的标识，可选）
    - **start_time**: 开始时间（可选），格式：YYYY-MM-DDTHH:MM:SS
    - **end_time**: 结束时间（可选），格式：YYYY-MM-DDTHH:MM:SS
    - **返回**: 包含价格变化记录的数据列表
    - **说明**: 如果不指定任何参数，默认查询最近24小时的变更记录
    """
    try:
        results = db_reader.get_price_changes(request_id, start_time, end_time)
        return {
            "request_id": request_id,
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "data_count": len(results),
            "data": results
        }
    except Exception as e:
        logger.error(f"查询价格变化接口异常: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)