import requests
import json

# 接口地址
url = "http://localhost:8000/api/price-history"

# 请求参数（注意时间格式需要符合YYYY-MM-DDTHH:MM:SS）
params = {
    "name": "活牛",
    "start_time": "2025-10-10T00:00:00",
    "end_time": "2025-10-15T23:59:59"
}

# 发送请求
try:
    print(f"正在调用接口: {url}")
    print(f"参数: name=活牛, start_time=2025-10-10T00:00:00, end_time=2025-10-15T23:59:59")
    
    response = requests.get(url, params=params)
    response.raise_for_status()  # 如果状态码不是200，抛出异常
    
    # 解析响应
    data = response.json()
    
    # 打印实际调用结果
    print("\n=== 接口二实际调用结果 ===")
    print(f"状态码: {response.status_code}")
    print(f"返回数据条数: {len(data)}")
    print("返回数据:")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    
    # 如果有数据，显示第一条和最后一条记录的详细信息
    if data:
        print("\n详细信息:")
        print(f"第一条记录 - 时间: {data[0]['create_time']}, 价格: {data[0]['price']}")
        if len(data) > 1:
            print(f"最后一条记录 - 时间: {data[-1]['create_time']}, 价格: {data[-1]['price']}")
    
    print("\n✅ 接口调用成功")
    
except requests.exceptions.RequestException as e:
    print(f"❌ 请求失败: {e}")
    if hasattr(e, 'response'):
        print(f"服务器响应: {e.response.status_code}")
        try:
            print(f"响应内容: {e.response.text}")
        except:
            pass
except ValueError as e:
    print(f"❌ JSON解析失败: {e}")
    print(f"原始响应: {response.text}")