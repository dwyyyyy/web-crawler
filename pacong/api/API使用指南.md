# API使用指南

## 概述
本指南提供了商品数据API的详细使用说明，帮助您正确调用各个接口获取商品价格数据。

## API服务状态
- ✅ API服务已成功启动在 http://localhost:8000
- ✅ 所有接口功能正常
- ✅ 数据库连接正常

## 解决Swagger UI/ReDoc显示问题的方法
如果浏览器中直接访问文档页面显示为空，可能是由于中文编码或浏览器缓存问题。以下是几种解决方法：

### 方法1：清除浏览器缓存
1. 按 `Ctrl+Shift+Delete` (Windows/Linux) 或 `Command+Shift+Delete` (Mac)
2. 选择清除所有缓存数据（特别是"Cookie和其他网站数据"和"缓存的图片和文件"）
3. 关闭并重新打开浏览器
4. 再次访问 http://localhost:8000/docs

### 方法2：尝试不同的浏览器
建议使用Chrome、Firefox或Edge浏览器，这些浏览器对Swagger UI有更好的兼容性。

### 方法3：直接使用API接口
即使没有文档界面，您仍然可以通过HTTP请求直接调用API接口。以下是各接口的详细使用说明：

## API接口详细说明

### 1. 根路径接口
**URL**: http://localhost:8000/
**方法**: GET
**功能**: 返回API版本信息和可用端点列表
**示例请求**:
```powershell
# 使用PowerShell测试
Invoke-WebRequest -Uri http://localhost:8000 -UseBasicParsing

# 使用curl测试（需要安装curl）
curl http://localhost:8000
```
**预期响应**: 包含API版本、可用端点和文档链接的JSON对象

### 2. 查询最新价格接口
**URL**: http://localhost:8000/api/latest-price
**方法**: GET
**参数**:
- `name`: 商品名称（必填）
**功能**: 查询指定商品的最新价格和涨跌幅
**示例请求**:
```powershell
# 注意：需要使用数据库中实际存在的商品名称
Invoke-WebRequest -Uri "http://localhost:8000/api/latest-price?name=黄金期货主力合约" -UseBasicParsing
```
**预期响应**: 包含商品最新价格信息的JSON对象，或404错误（如果商品不存在）

### 3. 查询历史数据接口
**URL**: http://localhost:8000/api/price-history
**方法**: GET
**参数**:
- `name`: 商品名称（必填）
- `start_time`: 开始时间（必填，格式：YYYY-MM-DDTHH:MM:SS）
- `end_time`: 结束时间（可选，格式：YYYY-MM-DDTHH:MM:SS）
**功能**: 查询指定商品在某时间段的价格历史
**示例请求**:
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/price-history?name=黄金期货主力合约&start_time=2023-01-01T00:00:00" -UseBasicParsing
```
**预期响应**: 包含商品历史价格数据的JSON对象

### 4. 查询价格变更记录接口
**URL**: http://localhost:8000/api/price-changes
**方法**: GET
**参数**:
- `request_id`: 请求ID（可选）
- `start_time`: 开始时间（可选，格式：YYYY-MM-DDTHH:MM:SS）
- `end_time`: 结束时间（可选，格式：YYYY-MM-DDTHH:MM:SS）
**功能**: 查看某次抓取或某时间段的价格变化
**说明**: 如果不指定任何参数，默认查询最近24小时的变更记录
**示例请求**:
```powershell
# 查询最近24小时的变更记录
Invoke-WebRequest -Uri http://localhost:8000/api/price-changes -UseBasicParsing

# 查询特定时间范围内的变更记录
Invoke-WebRequest -Uri "http://localhost:8000/api/price-changes?start_time=2023-01-01T00:00:00&end_time=2023-01-31T23:59:59" -UseBasicParsing
```
**预期响应**: 包含价格变化记录的数据列表

## 数据说明
- 当前数据库中可能没有商品数据，这是正常现象
- 建议先运行爬虫收集数据后再测试API接口
- 如需查看或修改数据库连接配置，请检查 `pacong/output/mysql_writer.py` 文件

## 常见问题排查

### 1. 接口返回404错误
- 原因：请求的商品在数据库中不存在
- 解决方案：使用数据库中实际存在的商品名称，或先运行爬虫收集数据

### 2. 接口返回500错误
- 原因：服务器内部错误，可能是数据库连接问题或SQL查询错误
- 解决方案：检查API服务日志获取详细错误信息

### 3. 启动API服务时出现端口占用错误
- 原因：8000端口已被其他程序占用
- 解决方案：
  ```powershell
  # 查找占用8000端口的进程ID
  netstat -ano | findstr :8000
  
  # 停止该进程
  Stop-Process -Id [进程ID] -Force
  
  # 使用其他端口启动API服务
  python -m pacong.api.run_api --host 0.0.0.0 --port [其他端口]
  ```

## 测试脚本使用
项目根目录下的 `test_api_calls.py` 脚本可以帮助您快速验证API服务是否正常工作：
```powershell
python test_api_calls.py
```

## 启动和停止API服务

### 启动API服务
```powershell
# 使用默认端口（8000）
python -m pacong.api.run_api

# 使用自定义端口
python -m pacong.api.run_api --port 8888
```

### 停止API服务
- 方法1：在运行API服务的终端窗口中按 `Ctrl+C`
- 方法2：通过任务管理器或命令行停止进程

## 联系支持
如果您遇到任何问题或需要进一步的帮助，请联系系统管理员。