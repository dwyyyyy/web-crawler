import requests
import json

# 接口地址
url = "http://localhost:8000/api/price-changes"

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
    print("\n=== 接口三实际调用结果 ===")
    print(f"状态码: {response.status_code}")
    print(f"返回数据结构:")
    print(f"  - name: {data.get('name')}")
    print(f"  - start_time: {data.get('start_time')}")
    print(f"  - end_time: {data.get('end_time')}")
    print(f"  - data_count: {data.get('data_count')}")
    print(f"  - data数组长度: {len(data.get('data', []))}")
    
    print("\n详细数据:")
    data_list = data.get('data', [])
    if data_list:
        # 打印所有数据记录
        for i, record in enumerate(data_list):
            print(f"\n记录 {i+1}:")
            print(f"  商品名称: {record.get('name')}")
            print(f"  价格: {record.get('current_price')}")
            print(f"  创建时间: {record.get('created_at')}")
            change_percent = record.get('calculated_change_percent')
            if change_percent is not None:
                print(f"  价格变化百分比: {change_percent:.6f}%")
            else:
                print(f"  价格变化百分比: 无(第一条记录或前一条价格为0)")
    else:
        print("  暂无数据")
    
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