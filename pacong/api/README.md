# 📊 商品数据API使用指南

## 概述

本API提供商品价格数据的查询功能，包括最新价格、历史价格和价格变化趋势的查询接口。

## 如何启动API服务



```bash
# 进入项目根目录
cd d:\11111\web-crawler

# 使用uvicorn运行FastAPI应用（开发模式）
uvicorn pacong.api.main:app --host 0.0.0.0 --port 8000 --reload
```



## API接口使用说明

### 1. 获取API信息

- **URL**: `/`
- **方法**: `GET`
- **功能**: 返回API基本信息和可用端点列表
- **示例响应**:
  ```json
  {
    "message": "欢迎使用商品数据API",
    "version": "1.0.0",
    "endpoints": [
      "/api/latest-price?name=商品名称",
      "/api/price-history?name=商品名称&start_time=2023-01-01T00:00:00",
      "/api/price-changes"
    ],
    "docs": "http://localhost:8000/docs"
  }
  ```

### 2. 查询最新价格

- **URL**: `/api/latest-price`
- **方法**: `GET`
- **参数**:
  - `name`: 商品名称（必填，例如：黄金期货主力合约）
- **功能**: 获取指定商品的最新价格信息
- **示例请求**:
  ```
  GET http://localhost:8000/api/latest-price?name=黄金期货主力合约
  ```
- **示例响应**:
  ```json
  {
    "price": 1923.50,
    "version_ts": "2024-01-15T10:30:45"
  }
  ```
- **错误响应** (404 Not Found):
  ```json
  {
    "detail": "未找到商品 '黄金期货主力合约' 的最新价格数据"
  }
  ```

### 3. 查询历史价格

- **URL**: `/api/price-history`
- **方法**: `GET`
- **参数**:
  - `name`: 商品名称（必填，例如：黄金期货主力合约）
  - `start_time`: 开始时间（必填，格式：YYYY-MM-DDTHH:MM:SS）
  - `end_time`: 结束时间（可选，格式：YYYY-MM-DDTHH:MM:SS，默认为当前时间）
- **功能**: 获取指定商品在某时间段内的价格历史记录
- **示例请求**:
  ```
  GET http://localhost:8000/api/price-history?name=黄金期货主力合约&start_time=2024-01-01T00:00:00
  ```
- **示例响应**:
  ```json
  [
    {
      "create_time": "2024-01-15T10:30:45",
      "price": 1923.50
    },
    {
      "create_time": "2024-01-15T09:30:45",
      "price": 1918.75
    }
  ]
  ```

### 4. 查询价格变化趋势

- **URL**: `/api/price-changes`
- **方法**: `GET`
- **参数**:
  - `name`: 商品名称（可选，例如：白银COMEX）
  - `start_time`: 开始时间（可选，格式：YYYY-MM-DDTHH:MM:SS）
  - `end_time`: 结束时间（可选，格式：YYYY-MM-DDTHH:MM:SS）
- **功能**: 查询商品的价格变化记录，自动计算价格变化百分比
- **说明**: 不指定参数时，默认查询最近24小时的所有商品数据
- **示例请求**:
  ```
  GET http://localhost:8000/api/price-changes?name=白银COMEX&start_time=2024-01-01T00:00:00
  ```
- **示例响应**:
  ```json
  {
    "name": "白银COMEX",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-01-15T23:59:59",
    "data_count": 2,
    "data": [
      {
        "name": "白银COMEX",
        "current_price": 24.50,
        "created_at": "2024-01-15T10:30:45",
        "calculated_change_percent": 0.82
      },
      {
        "name": "白银COMEX",
        "current_price": 24.30,
        "created_at": "2024-01-15T09:30:45"
      }
    ]
  }
  ```

## API文档访问

启动服务后，可以通过以下地址访问交互式API文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

在这些文档界面中，您可以直接在浏览器中测试API端点，查看参数说明和响应格式。

## 错误处理

API可能返回的常见错误码：

- **404 Not Found**: 请求的商品不存在
- **500 Internal Server Error**: 服务器内部错误
- **参数验证错误**: 请求参数不符合要求

所有错误响应都包含详细的错误描述信息。

## 使用注意事项

1. 时间参数必须使用ISO 8601格式：`YYYY-MM-DDTHH:MM:SS`
2. API默认在8000端口启动
3. 使用`--reload`参数运行时，修改代码会自动重启服务
4. 默认查询限制为1000条记录