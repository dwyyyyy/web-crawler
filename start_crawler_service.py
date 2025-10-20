#!/usr/bin/env python3
"""
启动爬虫服务脚本
用于启动运行在 http://localhost:8001 的爬虫服务
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).absolute().parent
sys.path.insert(0, str(project_root))

def main():
    """
    主函数，启动爬虫服务
    """
    print("🚀 启动爬虫服务...")
    print(f"📁 项目根目录: {project_root}")
    print(f"🌐 服务将运行在: http://localhost:8001")
    print(f"📖 API文档: http://localhost:8001/docs")
    print("=" * 50)
    
    try:
        # 导入必要的模块
        import uvicorn
        from pacong.api.crawler_service import app
        
        # 启动服务
        uvicorn.run(
            "pacong.api.crawler_service:app",
            host="0.0.0.0",
            port=8001,
            reload=True,
            log_level="info"
        )
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        print("请确保已安装所有依赖:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 启动服务失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()