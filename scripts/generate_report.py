#!/usr/bin/env python3
"""
生成延迟监控报告和可视化图表
"""

import json
import os
import glob
from datetime import datetime, timezone, timedelta
from collections import defaultdict

DATA_DIR = "data"
DOCS_DIR = "docs"

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def load_all_data():
    """加载所有历史数据"""
    all_records = []
    pattern = os.path.join(DATA_DIR, "*.jsonl")
    
    for filepath in sorted(glob.glob(pattern)):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        all_records.append(record)
                    except json.JSONDecodeError:
                        continue
    
    return all_records

def calculate_stats(records):
    """计算统计数据"""
    successful = [r for r in records if r.get('success')]
    failed = [r for r in records if not r.get('success')]
    
    if not successful:
        return None
    
    ttfb_values = [r['ttfb_ms'] for r in successful if r.get('ttfb_ms')]
    total_values = [r['total_ms'] for r in successful if r.get('total_ms')]
    dns_values = [r['dns_ms'] for r in successful if r.get('dns_ms')]
    tcp_values = [r['tcp_ms'] for r in successful if r.get('tcp_ms')]
    
    def stats(values):
        if not values:
            return {"min": None, "max": None, "avg": None, "p95": None}
        sorted_v = sorted(values)
        n = len(sorted_v)
        return {
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "avg": round(sum(values) / len(values), 2),
            "p95": round(sorted_v[int(n * 0.95)] if n > 1 else sorted_v[0], 2)
        }
    
    return {
        "total_checks": len(records),
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": round(len(successful) / len(records) * 100, 2) if records else 0,
        "ttfb": stats(ttfb_values),
        "total": stats(total_values),
        "dns": stats(dns_values),
        "tcp": stats(tcp_values)
    }

def generate_html_report(records):
    """生成 HTML 可视化报告"""
    ensure_dir(DOCS_DIR)
    
    # 最近 24 小时的数据
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)
    recent_records = [r for r in records 
                      if datetime.fromisoformat(r['timestamp'].replace('Z', '+00:00')) > day_ago]
    
    # 最近 7 天的数据
    week_ago = now - timedelta(days=7)
    week_records = [r for r in records 
                    if datetime.fromisoformat(r['timestamp'].replace('Z', '+00:00')) > week_ago]
    
    stats_all = calculate_stats(records)
    stats_24h = calculate_stats(recent_records)
    stats_7d = calculate_stats(week_records)
    
    # 生成图表数据
    chart_data = []
    for r in records[-288:]:  # 最近 48 小时 (每 10 分钟一条)
        if r.get('success'):
            chart_data.append({
                "time": r['timestamp'][:19].replace('T', ' '),
                "ttfb": r.get('ttfb_ms'),
                "total": r.get('total_ms'),
                "dns": r.get('dns_ms'),
                "tcp": r.get('tcp_ms')
            })
    
    chart_json = json.dumps(chart_data)
    
    # 生成每日汇总
    daily_data = defaultdict(lambda: {"count": 0, "success": 0, "ttfb_sum": 0, "ttfb_count": 0})
    for r in records:
        day = r['timestamp'][:10]
        daily_data[day]["count"] += 1
        if r.get('success'):
            daily_data[day]["success"] += 1
            if r.get('ttfb_ms'):
                daily_data[day]["ttfb_sum"] += r['ttfb_ms']
                daily_data[day]["ttfb_count"] += 1
    
    daily_rows = ""
    for day in sorted(daily_data.keys(), reverse=True)[:30]:
        d = daily_data[day]
        avg_ttfb = round(d["ttfb_sum"] / d["ttfb_count"], 2) if d["ttfb_count"] > 0 else "N/A"
        success_rate = round(d["success"] / d["count"] * 100, 1)
        daily_rows += f"""
        <tr>
            <td>{day}</td>
            <td>{d['count']}</td>
            <td>{d['success']}/{d['count']} ({success_rate}%)</td>
            <td>{avg_ttfb} ms</td>
        </tr>
        """
    
    def format_stats(s):
        if not s:
            return "<p>暂无数据</p>"
        return f"""
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{s['success_rate']}%</div>
                <div class="stat-label">成功率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{s['ttfb']['avg']} ms</div>
                <div class="stat-label">TTFB 平均</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{s['total']['avg']} ms</div>
                <div class="stat-label">总耗时平均</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{s['ttfb']['p95']} ms</div>
                <div class="stat-label">TTFB P95</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{s['ttfb']['min']} ms</div>
                <div class="stat-label">TTFB 最小</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{s['ttfb']['max']} ms</div>
                <div class="stat-label">TTFB 最大</div>
            </div>
        </div>
        """
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌐 xmhai.cn 延迟监控</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{
            text-align: center;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2rem;
        }}
        .subtitle {{
            text-align: center;
            color: #94a3b8;
            margin-bottom: 30px;
        }}
        .update-time {{
            text-align: center;
            color: #64748b;
            font-size: 0.85rem;
            margin-bottom: 30px;
        }}
        .section {{
            background: #1e293b;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid #334155;
        }}
        .section h2 {{
            margin-bottom: 20px;
            color: #60a5fa;
            font-size: 1.2rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 16px;
        }}
        .stat-card {{
            background: #0f172a;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid #334155;
            transition: transform 0.2s, border-color 0.2s;
        }}
        .stat-card:hover {{
            transform: translateY(-2px);
            border-color: #60a5fa;
        }}
        .stat-value {{
            font-size: 1.8rem;
            font-weight: 700;
            color: #60a5fa;
            margin-bottom: 4px;
        }}
        .stat-label {{
            color: #94a3b8;
            font-size: 0.85rem;
        }}
        .chart-container {{
            position: relative;
            height: 350px;
            margin-top: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #334155;
        }}
        th {{
            color: #94a3b8;
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
        }}
        tr:hover td {{
            background: #0f172a;
        }}
        .status-good {{ color: #4ade80; }}
        .status-warn {{ color: #fbbf24; }}
        .status-bad {{ color: #f87171; }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .badge-success {{ background: #064e3b; color: #4ade80; }}
        .badge-fail {{ background: #450a0a; color: #f87171; }}
        @media (max-width: 768px) {{
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .stat-value {{ font-size: 1.4rem; }}
            h1 {{ font-size: 1.5rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌐 xmhai.cn 网站延迟监控</h1>
        <p class="subtitle">定时检测网站响应性能 | 每 10 分钟采集一次</p>
        <p class="update-time">🕐 最后更新: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        
        <div class="section">
            <h2>📊 最近 24 小时</h2>
            {format_stats(stats_24h)}
        </div>
        
        <div class="section">
            <h2>📈 最近 7 天</h2>
            {format_stats(stats_7d)}
        </div>
        
        <div class="section">
            <h2>📉 延迟趋势 (最近 48 小时)</h2>
            <div class="chart-container">
                <canvas id="latencyChart"></canvas>
            </div>
        </div>
        
        <div class="section">
            <h2>📋 每日汇总 (最近 30 天)</h2>
            <table>
                <thead>
                    <tr>
                        <th>日期</th>
                        <th>检测次数</th>
                        <th>成功/总计</th>
                        <th>平均 TTFB</th>
                    </tr>
                </thead>
                <tbody>
                    {daily_rows}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>📊 全部历史统计</h2>
            {format_stats(stats_all)}
        </div>
    </div>
    
    <script>
        const chartData = {chart_json};
        const labels = chartData.map(d => d.time);
        
        new Chart(document.getElementById('latencyChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{
                        label: 'TTFB (ms)',
                        data: chartData.map(d => d.ttfb),
                        borderColor: '#60a5fa',
                        backgroundColor: 'rgba(96, 165, 250, 0.1)',
                        tension: 0.3,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        fill: true
                    }},
                    {{
                        label: 'DNS (ms)',
                        data: chartData.map(d => d.dns),
                        borderColor: '#f472b6',
                        backgroundColor: 'transparent',
                        tension: 0.3,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        borderDash: [5, 5]
                    }},
                    {{
                        label: 'TCP (ms)',
                        data: chartData.map(d => d.tcp),
                        borderColor: '#4ade80',
                        backgroundColor: 'transparent',
                        tension: 0.3,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        borderDash: [2, 2]
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                interaction: {{
                    mode: 'index',
                    intersect: false,
                }},
                plugins: {{
                    legend: {{
                        labels: {{ color: '#94a3b8' }}
                    }},
                    tooltip: {{
                        backgroundColor: '#1e293b',
                        titleColor: '#e2e8f0',
                        bodyColor: '#e2e8f0',
                        borderColor: '#334155',
                        borderWidth: 1
                    }}
                }},
                scales: {{
                    x: {{
                        ticks: {{
                            color: '#64748b',
                            maxTicksLimit: 12
                        }},
                        grid: {{
                            color: '#334155',
                            drawBorder: false
                        }}
                    }},
                    y: {{
                        ticks: {{ color: '#64748b' }},
                        grid: {{
                            color: '#334155',
                            drawBorder: false
                        }},
                        title: {{
                            display: true,
                            text: '延迟 (ms)',
                            color: '#94a3b8'
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    
    filepath = os.path.join(DOCS_DIR, "index.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"📊 报告已生成: {filepath}")
    return filepath

def main():
    print("📊 正在生成监控报告...")
    records = load_all_data()
    print(f"📁 加载了 {len(records)} 条历史记录")
    
    if not records:
        print("⚠️ 暂无数据")
        return
    
    generate_html_report(records)
    print("✅ 报告生成完成!")

if __name__ == "__main__":
    main()