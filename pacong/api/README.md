# 📊 商品数据API文档

## 概述

本目录包含基于FastAPI开发的商品数据RESTful API服务，提供对商品价格数据的查询功能。API服务通过连接MySQL数据库，提供商品最新价格、历史价格和价格变更记录的查询接口。

## 目录结构

```
pacong/api/
├── __init__.py  # 包初始化文件
├── main.py      # FastAPI主应用文件
└── README.md    # API文档（本文件）
```

## API功能介绍

### 1. 查询最新价格

获取指定商品的最新价格、涨跌幅及相关信息。

- **URL**: `/api/latest-price`
- **方法**: `GET`
- **参数**:
  - `name`: 商品名称（必填，例如：黄金期货主力合约）
- **返回格式**: JSON对象，包含商品名称、当前价格、涨跌幅、货币单位、数据来源、更新时间等信息
- **示例请求**:
  ```
  GET http://localhost:8000/api/latest-price?name=黄金期货主力合约
  ```

### 2. 查询历史数据

获取指定商品在某时间段内的价格历史数据。

- **URL**: `/api/price-history`
- **方法**: `GET`
- **参数**:
  - `name`: 商品名称（必填，例如：黄金期货主力合约）
  - `start_time`: 开始时间（必填，格式：YYYY-MM-DDTHH:MM:SS）
  - `end_time`: 结束时间（可选，格式：YYYY-MM-DDTHH:MM:SS，默认为当前时间）
- **返回格式**: JSON对象，包含查询条件、数据总量和历史数据列表
- **示例请求**:
  ```
  GET http://localhost:8000/api/price-history?name=黄金期货主力合约&start_time=2023-01-01T00:00:00
  ```

### 3. 查询变更记录

查看某次抓取或某时间段内的价格变化记录。

- **URL**: `/api/price-changes`
- **方法**: `GET`
- **参数**:
  - `request_id`: 请求ID（可选，某次抓取的标识）
  - `start_time`: 开始时间（可选，格式：YYYY-MM-DDTHH:MM:SS）
  - `end_time`: 结束时间（可选，格式：YYYY-MM-DDTHH:MM:SS）
- **返回格式**: JSON对象，包含查询条件、数据总量和变更记录列表
- **说明**: 如果不指定任何参数，默认查询最近24小时的变更记录
- **示例请求**:
  ```
  GET http://localhost:8000/api/price-changes?start_time=2023-01-01T00:00:00&end_time=2023-01-07T00:00:00
  ```

## 项目配置与依赖

### 主要依赖

- fastapi==0.115.0：构建高性能API的框架
- uvicorn==0.32.0：ASGI服务器，用于运行FastAPI应用
- pydantic==2.9.2：数据验证和设置管理
- PyMySQL==1.1.2：MySQL数据库驱动

### 数据库配置

数据库连接信息在`main.py`文件中配置：

```python
db_reader = MySQLReader(
    host='',
    port=3306,
    user='root',
    password='',
    database='pacong'
)
```

> **注意**：生产环境中建议将敏感信息（如数据库密码）存储在环境变量或配置文件中。

## 启动API服务

### 方法一：直接运行main.py

```bash
# 进入api目录
cd d:\web-crawler\pacong\api

# 运行main.py
python main.py
```

### 方法二：使用uvicorn命令

```bash
# 在项目根目录执行
uvicorn pacong.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 方法三：通过项目主入口

```bash
# 在项目根目录执行
python -m pacong.main --api-only
```

## API文档访问

启动服务后，可以通过以下地址访问自动生成的交互式API文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 错误处理

API提供了以下错误处理机制：

- 404 Not Found：当请求的商品不存在时返回
- 500 Internal Server Error：当服务器内部发生错误时返回
- 参数验证错误：当请求参数不符合要求时返回

## 开发说明

### 扩展API功能

如需添加新的API端点，请按照以下步骤操作：

1. 在`MySQLReader`类中添加新的数据查询方法
2. 在主应用中使用`@app.get()`、`@app.post()`等装饰器添加新的路由
3. 为新接口添加适当的文档字符串和参数验证
4. 实现错误处理逻辑

### 代码风格规范

- 函数和方法应有详细的文档字符串，包括参数、返回值和可能的异常
- 错误处理应包含适当的日志记录
- 使用类型注解提高代码可读性和可维护性
- 保持代码风格一致，遵循PEP 8规范

## 测试

API测试文件位于`tests/test_api_endpoints.py`，包含对所有接口的功能测试。可以使用以下命令运行测试：

```bash
# 在项目根目录执行
python -m unittest pacong.tests.test_api_endpoints
```

## 注意事项

1. 生产环境中应限制CORS允许的域名，不要使用通配符`*`
2. 考虑添加API认证和授权机制，保护敏感数据
3. 对于高流量场景，建议添加请求限流和缓存机制
4. 定期备份数据库，确保数据安全
5. 监控API性能和错误率，及时发现并解决问题

## 版本历史

- v1.0.0：初始版本，提供三个主要API接口
  - 查询最新价格
  - 查询历史数据
  - 查询变更记录