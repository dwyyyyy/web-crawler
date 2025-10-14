"""
FastAPI服务启动脚本
用于启动商品数据API服务
"""
import uvicorn
import argparse
from ..core import get_logger

logger = get_logger(__name__)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='启动商品数据API服务')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='服务器主机地址')
    parser.add_argument('--port', type=int, default=8000, help='服务器端口')
    parser.add_argument('--reload', action='store_true', help='开发模式自动重载')
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    logger.info(f"准备启动商品数据API服务...")
    logger.info(f"访问地址: http://{args.host}:{args.port}")
    logger.info(f"API文档: http://{args.host}:{args.port}/docs")
    
    try:
        uvicorn.run(
            "pacong.api.main_no_db:app",
            host=args.host,
            port=args.port,
            reload=args.reload
        )
    except KeyboardInterrupt:
        logger.info("API服务已停止")
    except Exception as e:
        logger.error(f"API服务启动失败: {e}")

if __name__ == "__main__":
    main()