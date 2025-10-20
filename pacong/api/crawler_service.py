"""
爬虫服务API
提供爬虫执行和健康检查的RESTful接口
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import json
import asyncio

# 添加项目根目录到Python路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from pacong.core import get_logger, init_config, init_logging
from pacong.services import CommodityService
from pacong.scrapers import ScraperFactory

# 创建FastAPI应用
app = FastAPI(
    title="爬虫服务API",
    description="提供爬虫执行和健康检查的RESTful接口",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "基础接口",
            "description": "API基本功能接口"
        },
        {
            "name": "爬虫接口",
            "description": "爬虫执行相关接口"
        }
    ]
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

# 初始化配置和日志
config = init_config()
logger = init_logging()

# 爬虫任务状态跟踪
class TaskStatusTracker:
    def __init__(self):
        self.tasks = {}
    
    def add_task(self, task_id: str, task_info: Dict[str, Any]):
        self.tasks[task_id] = {
            "status": "running",
            "result": None,
            "error": None,
            "created_at": task_info.get("created_at", None),
            "scrapers": task_info.get("scrapers", []),
            "options": task_info.get("options", {})
        }
    
    def update_task(self, task_id: str, status: str, result: Any = None, error: str = None):
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = status
            if result is not None:
                self.tasks[task_id]["result"] = result
            if error is not None:
                self.tasks[task_id]["error"] = error
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.tasks.get(task_id)
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        return [{
            "task_id": task_id,
            "status": task_info["status"],
            "created_at": task_info["created_at"],
            "scrapers": task_info["scrapers"]
        } for task_id, task_info in self.tasks.items()]

# 全局任务跟踪器
task_tracker = TaskStatusTracker()

# 请求模型
class CrawlRequest(BaseModel):
    # 使用明确的可选标记并添加OpenAPI注释
    scrapers: Optional[List[str]] = Field(
        default=None, 
        description="可选，要执行的爬虫名称列表，不指定则执行所有可用爬虫"
    )
    output_to_file: bool = False  # 是否输出到文件
    log_level: str = "INFO"  # 日志级别



# 初始化服务
commodity_service = CommodityService()

@app.get("/health", summary="健康检查", tags=["基础接口"])
async def health_check():
    """
    健康检查接口
    
    返回服务运行状态、可用爬虫列表等信息
    """
    try:
        # 获取可用爬虫列表
        available_scrapers = ScraperFactory.list_available_scrapers()
        
        # 获取当前运行中的任务数
        running_tasks = sum(1 for task in task_tracker.tasks.values() if task["status"] == "running")
        
        return {
            "status": "healthy",
            "message": "爬虫服务运行正常",
            "available_scrapers": available_scrapers,
            "running_tasks": running_tasks,
            "total_tasks": len(task_tracker.tasks),
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"服务健康检查失败: {str(e)}")

@app.post("/crawl", summary="执行爬取任务", tags=["爬虫接口"])
async def crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """
    执行爬取任务
    
    - **scrapers**: 可选，要执行的爬虫名称列表，不指定则执行所有可用爬虫
    - **output_to_file**: 是否输出结果到文件（CSV和Excel）
    - **log_level**: 日志级别（DEBUG, INFO, WARNING, ERROR）
    
    返回任务ID和初始状态，任务将在后台执行
    """
    try:
        # 获取可用爬虫列表
        available_scrapers = ScraperFactory.list_available_scrapers()
        
        # 验证爬虫名称（如果提供）
        if request.scrapers:
            invalid_scrapers = [name for name in request.scrapers if name not in available_scrapers]
            if invalid_scrapers:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的爬虫名称: {', '.join(invalid_scrapers)}。可用爬虫: {', '.join(available_scrapers)}"
                )
        
        # 生成任务ID
        import uuid
        import datetime
        task_id = str(uuid.uuid4())
        task_info = {
            "task_id": task_id,
            "created_at": datetime.datetime.now().isoformat(),
            "scrapers": request.scrapers or available_scrapers,
            "options": {
                "output_to_file": request.output_to_file,
                "log_level": request.log_level
            }
        }
        
        # 注册任务
        task_tracker.add_task(task_id, task_info)
        
        # 在后台执行爬虫任务
        background_tasks.add_task(
            _run_crawl_task,
            task_id,
            request.scrapers,
            request.output_to_file,
            request.log_level
        )
        
        return {
            "task_id": task_id,
            "status": "running",
            "message": "爬取任务已启动",
            "details": task_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建爬取任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建爬取任务失败: {str(e)}")

@app.get("/tasks/{task_id}", summary="获取任务状态", tags=["爬虫接口"])
async def get_task_status(task_id: str):
    """
    获取指定任务的执行状态和结果
    
    - **task_id**: 任务ID
    """
    task = task_tracker.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    
    return {
        "task_id": task_id,
        "status": task["status"],
        "created_at": task["created_at"],
        "scrapers": task["scrapers"],
        "result": task["result"],
        "error": task["error"]
    }

@app.get("/tasks", summary="列出所有任务", tags=["爬虫接口"])
async def list_tasks():
    """
    列出所有任务的基本信息
    """
    return {
        "tasks": task_tracker.list_tasks(),
        "total": len(task_tracker.tasks)
    }

@app.get("/scrapers", summary="列出可用爬虫", tags=["基础接口"])
async def list_available_scrapers():
    """
    列出所有可用的爬虫名称
    """
    try:
        scrapers = ScraperFactory.list_available_scrapers()
        return {
            "scrapers": scrapers,
            "count": len(scrapers)
        }
    except Exception as e:
        logger.error(f"获取可用爬虫列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取可用爬虫列表失败: {str(e)}")

async def _run_crawl_task(task_id: str, scrapers: Optional[List[str]], output_to_file: bool, log_level: str):
    """
    在后台运行爬取任务的函数
    """
    import traceback
    
    try:
        # 临时修改日志级别
        original_level = config.get('logging.level')
        if log_level != original_level:
            config.set('logging.level', log_level)
            # 重新初始化日志
            global logger
            logger = init_logging()
        
        logger.info(f"开始执行任务 {task_id}")
        logger.info(f"爬取参数: scrapers={scrapers}, output_to_file={output_to_file}, log_level={log_level}")
        
        # 执行爬取任务
        result = commodity_service.run_full_analysis(scrapers, output_to_file)
        
        # 更新任务状态为完成
        task_tracker.update_task(task_id, "completed", result=result)
        logger.info(f"任务 {task_id} 执行完成")
        
    except Exception as e:
        # 记录异常
        error_msg = str(e)
        error_trace = traceback.format_exc()
        logger.error(f"任务 {task_id} 执行失败: {error_msg}\n{error_trace}")
        
        # 更新任务状态为失败
        task_tracker.update_task(task_id, "failed", error=error_msg)
    finally:
        # 恢复原始日志级别
        if log_level != original_level:
            config.set('logging.level', original_level)
            logger = init_logging()

if __name__ == "__main__":
    import uvicorn
    # 运行在8001端口
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)