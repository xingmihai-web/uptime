# 🌐 xmhai.cn 网站延迟监控

[![Latency Monitor](https://github.com/xingmihai-web/uptime/actions/workflows/latency-monitor.yml/badge.svg)](https://github.com/xingmihai-web/uptime/actions/workflows/latency-monitor.yml)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live-brightgreen)](https://xingmihai-web.github.io/uptime/)

&gt; 定时监控 https://www.xmhai.cn 的网站响应延迟，每 10 分钟采集一次数据。

## 📊 查看报告

👉 **[点击在线查看监控报告](https://xingmihai-eeb.github.io/uptime/)**

## 🔧 监控指标

| 指标 | 说明 |
|------|------|
| DNS | DNS 解析延迟 |
| TCP | TCP 连接建立延迟 |
| TTFB | Time To First Byte，首字节时间 |
| Total | 完整请求总耗时 |

## 🚀 部署步骤

1. **Fork 或创建新仓库**，将上述文件放入仓库
2. **启用 GitHub Pages**:
   - Settings → Pages → Source → Deploy from a branch → `main` / `docs` folder
3. **修改工作流权限**:
   - Settings → Actions → General → Workflow permissions → Read and write permissions
4. **手动触发一次**工作流，或等待定时执行

## ⚙️ 自定义配置

编辑 `.github/workflows/latency-monitor.yml` 中的 cron 表达式：

```yaml
# 每 10 分钟
- cron: '*/10 * * * *'

# 每小时
- cron: '0 * * * *'

# 每 5 分钟
- cron: '*/5 * * * *'