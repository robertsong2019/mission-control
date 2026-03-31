# Mission Control 教程

本教程帮助你从零开始部署和使用 Mission Control Dashboard。

## 📖 目录

1. [5 分钟快速部署](#5-分钟快速部署)
2. [理解数据格式](#理解数据格式)
3. [配置自动更新](#配置自动更新)
4. [自定义外观](#自定义外观)
5. [常见问题](#常见问题)

---

## 5 分钟快速部署

### 前提条件

- 一个 GitHub 账号
- 一个运行 OpenClaw 的服务器（可选，用于自动更新）

### 步骤

#### 1. 创建仓库

```bash
# 在 GitHub 上创建新仓库 mission-control，然后：
git clone https://github.com/你的用户名/mission-control.git
cd mission-control
```

#### 2. 添加文件

将 `index.html` 和 `data/dashboard-data.json` 放入仓库根目录。

#### 3. 开启 GitHub Pages

1. 进入仓库 **Settings → Pages**
2. Source 选择 **Deploy from branch**
3. Branch 选 **main**，文件夹选 **/ (root)**
4. 点击 **Save**

等待 1-2 分钟，访问 `https://你的用户名.github.io/mission-control/` 即可看到仪表板。

#### 4. 修改 PIN

编辑 `index.html`，找到 `PIN: '1234'` 改为你自己的密码。

🎉 完成！你的仪表板已经上线。

---

## 理解数据格式

仪表板通过 `data/dashboard-data.json` 获取数据。以下是各字段的含义：

```json
{
  "lastUpdated": "2026-04-01T04:00:00Z",
  
  "actionRequired": [
    {
      "id": "1",
      "priority": "high",        // high | medium | low
      "title": "部署失败",
      "description": "生产环境需要关注",
      "source": "cron:deploy-check"
    }
  ],
  
  "activeNow": [
    {
      "id": "1",
      "name": "代码审查",
      "status": "running",       // running | pending | completed
      "startedAt": "2026-04-01T03:00:00Z",
      "details": "PR #42 审查中"
    }
  ],
  
  "products": [
    {
      "name": "API 服务",
      "status": "healthy",       // healthy | degraded | down
      "uptime": "99.9%",
      "lastCheck": "2026-04-01T03:55:00Z"
    }
  ],
  
  "crons": [
    {
      "name": "健康检查",
      "schedule": "*/30 * * * *",
      "lastRun": "2026-04-01T03:30:00Z",
      "lastStatus": "success",   // success | error | timeout
      "errorCount": 0,
      "nextRun": "2026-04-01T04:00:00Z"
    }
  ],
  
  "recentActivity": [
    {
      "time": "2026-04-01T03:45:00Z",
      "type": "task_completed",  // task_completed | error | deployment | alert
      "message": "构建完成",
      "details": "v2.1.0 部署成功"
    }
  ]
}
```

### 字段优先级

- `priority`: `high` > `medium` > `low`（红色 > 黄色 > 蓝色）
- `status`: `running`（绿色动画）> `pending`（黄色）> `completed`（灰色）
- `lastStatus`: `error`（红色）> `timeout`（黄色）> `success`（绿色）

---

## 配置自动更新

### 使用 OpenClaw Cron

在你的 OpenClaw 配置中添加一个定时任务：

```yaml
name: Dashboard Update
schedule: "*/30 * * * *"
prompt: |
  更新 Mission Control 仪表板数据：
  
  1. 运行 cron list 获取所有任务状态
  2. 运行 sessions list 获取活跃会话
  3. 构建符合 schema 的 JSON 数据
  4. 写入 data/dashboard-data.json
  5. git commit 并 push
```

### 使用 GitHub Actions

也可以创建 `.github/workflows/update-dashboard.yml`：

```yaml
name: Update Dashboard
on:
  schedule:
    - cron: '*/30 * * * *'
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Generate data
        run: |
          # 你的数据生成逻辑
          echo '{"lastUpdated":"'$(date -uIs)'"}' > data/dashboard-data.json
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "Update dashboard data"
```

---

## 自定义外观

### 修改配色

编辑 `index.html` 中 `:root` 部分的 CSS 变量：

```css
:root {
    /* 改为暖色调 */
    --bg-primary: #1a0a00;
    --accent-blue: #f97316;  /* 改为橙色 */
}
```

### 修改刷新间隔

找到 `CONFIG` 对象，修改 `refreshInterval`：

```javascript
const CONFIG = {
    refreshInterval: 30000,  // 30秒，改为 60000 = 1分钟
};
```

### 隐藏某些板块

在 HTML 中注释掉不需要的 section：

```html
<!-- <section id="products-section">...</section> -->
```

---

## 常见问题

### Q: 页面显示空白？

检查浏览器控制台是否有错误。确认 `data/dashboard-data.json` 路径正确且 JSON 格式有效。

### Q: 数据不更新？

1. 确认 GitHub Pages 已启用
2. 检查数据文件是否已 push 到 main 分支
3. GitHub Pages 缓存可能需要 1-2 分钟更新

### Q: PIN 输入后没反应？

确认 PIN 与 `index.html` 中的 `CONFIG.PIN` 一致。

### Q: 能否用于私有仓库？

可以，但 GitHub Pages 只在 GitHub Pro/Team/Enterprise 中支持私有仓库。

### Q: 移动端体验不好？

Dashboard 已做了响应式设计。如有问题，请提交 Issue 并附上设备信息。
