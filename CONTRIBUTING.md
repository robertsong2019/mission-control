# 贡献指南

感谢你对 Mission Control Dashboard 的关注！欢迎任何形式的贡献。

## 🛠️ 开发环境

本项目是一个纯前端单页应用，无需构建工具：

1. Fork 本仓库
2. Clone 到本地
3. 用浏览器直接打开 `index.html` 即可运行

## 📝 如何贡献

### 报告 Bug

- 在 [Issues](https://github.com/robertsong2019/mission-control/issues) 中创建新 issue
- 描述问题、复现步骤、浏览器版本

### 功能建议

- 同样通过 Issues 提交
- 说明使用场景和预期效果

### 提交代码

1. 创建功能分支：`git checkout -b feature/your-feature`
2. 修改代码
3. 确保在主流浏览器中测试通过（Chrome、Firefox、Safari）
4. 提交 PR，描述改动内容

## 📐 代码规范

- 使用 CSS 变量保持配色一致（`index.html` 中的 `:root` 部分）
- 保持单文件结构，便于部署到 GitHub Pages
- JavaScript 使用现代 ES6+ 语法
- 数据格式遵循 `data/dashboard-data.json` 中的 schema

## 🏗️ 架构说明

```
mission-control/
├── index.html          # 所有 HTML + CSS + JS（单文件应用）
└── data/
    └── dashboard-data.json  # 仪表板数据
```

设计理念：**零依赖、单文件、开箱即用**。

## 💡 贡献方向

- 🌐 多语言支持
- 📊 新的图表/可视化组件
- 🔐 更强的认证方案
- 📱 PWA 支持（离线访问）
- 🎨 主题切换（亮色/暗色）
