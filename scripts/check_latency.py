#!/usr/bin/env python3
"""
Website Latency Monitor
定时检测网站响应延迟并记录数据
"""

import json
import time
import os
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse
import requests

# ============ 配置 ============
TARGET_URL = "https://www.xmhai.cn"
TIMEOUT = 30  # 请求超时时间(秒)
MAX_RETRIES = 3  # 失败重试次数
DATA_DIR = "data"
# ==============================

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def check_dns_latency(hostname):
    """检测 DNS 解析延迟"""
    start = time.perf_counter()
    try:
        socket.getaddrinfo(hostname, None)
        dns_time = (time.perf_counter() - start) * 1000
        return round(dns_time, 2)
    except Exception as e:
        return None

def check_tcp_latency(hostname, port=443):
    """检测 TCP 连接延迟"""
    start = time.perf_counter()
    try:
        sock = socket.create_connection((hostname, port), timeout=5)
        tcp_time = (time.perf_counter() - start) * 1000
        sock.close()
        return round(tcp_time, 2)
    except Exception as e:
        return None

def check_http_latency(url):
    """检测 HTTP 请求各阶段延迟"""
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "success": False,
        "dns_ms": None,
        "tcp_ms": None,
        "tls_ms": None,
        "ttfb_ms": None,  # Time To First Byte
        "total_ms": None,
        "status_code": None,
        "content_length": None,
        "error": None
    }
    
    parsed = urlparse(url)
    hostname = parsed.netloc or parsed.path
    
    # DNS 解析延迟
    result["dns_ms"] = check_dns_latency(hostname)
    
    # TCP 连接延迟
    result["tcp_ms"] = check_tcp_latency(hostname)
    
    # HTTP 请求延迟
    for attempt in range(MAX_RETRIES):
        try:
            start = time.perf_counter()
            response = requests.get(
                url, 
                timeout=TIMEOUT,
                allow_redirects=True,
                stream=True  # 使用流式读取以准确测量 TTFB
            )
            
            # 获取响应头的时间 = TTFB
            ttfb = (time.perf_counter() - start) * 1000
            
            # 读取完整内容
            content = response.content
            total = (time.perf_counter() - start) * 1000
            
            result.update({
                "success": True,
                "ttfb_ms": round(ttfb, 2),
                "total_ms": round(total, 2),
                "status_code": response.status_code,
                "content_length": len(content),
                "error": None
            })
            break
            
        except requests.exceptions.Timeout:
            result["error"] = f"Timeout (attempt {attempt + 1}/{MAX_RETRIES})"
        except requests.exceptions.ConnectionError as e:
            result["error"] = f"Connection error: {str(e)}"
        except Exception as e:
            result["error"] = f"Error: {str(e)}"
        
        if attempt < MAX_RETRIES - 1:
            time.sleep(2)
    
    return result

def save_result(result):
    """保存检测结果"""
    ensure_dir(DATA_DIR)
    
    # 按日期分文件存储
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filepath = os.path.join(DATA_DIR, f"{date_str}.jsonl")
    
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    
    # 同时保存最新结果
    latest_path = os.path.join(DATA_DIR, "latest.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return filepath

def print_result(result):
    """打印检测结果"""
    print("=" * 50)
    print(f"🕐 时间: {result['timestamp']}")
    print(f"🔗 URL: {result['url']}")
    
    if result['success']:
        print(f"✅ 状态: 成功 (HTTP {result['status_code']})")
        print(f"📡 DNS 解析: {result['dns_ms']} ms")
        print(f"🔌 TCP 连接: {result['tcp_ms']} ms")
        print(f"⏱️  TTFB: {result['ttfb_ms']} ms")
        print(f"📦 总耗时: {result['total_ms']} ms")
        print(f"📄 内容大小: {result['content_length']} bytes")
    else:
        print(f"❌ 状态: 失败")
        print(f"💥 错误: {result['error']}")
    print("=" * 50)

def main():
    print("🚀 开始检测网站延迟...")
    print(f"🎯 目标: {TARGET_URL}")
    
    result = check_http_latency(TARGET_URL)
    filepath = save_result(result)
    print_result(result)
    
    print(f"\n💾 数据已保存到: {filepath}")
    
    # 如果失败，返回非零退出码
    if not result['success']:
        print("\n⚠️ 检测失败!")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())