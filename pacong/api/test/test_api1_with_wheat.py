import requests
import json

# 接口地址
url = "http://localhost:8000/api/latest-price"

# 请求参数
params = {
    "name": "小麦"
}

# 发送请求
try:
    print(f"正在调用接口: {url}?name=小麦")
    response = requests.get(url, params=params)
    response.raise_for_status()  # 如果状态码不是200，抛出异常
    
    # 解析响应
    data = response.json()
    
    # 打印实际调用结果
    print("\n=== 接口一实际调用结果 ===")
    print(f"状态码: {response.status_code}")
    print("返回数据:")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    
    # 单独打印每个字段的值
    print("\n字段详情:")
    for key, value in data.items():
        print(f"{key}: {value}")
    
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