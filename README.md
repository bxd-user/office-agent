# Office Agent

> 基于 AI 的 Office 自动化工具：根据提示词自主规划并处理 Excel / Word 等文件。

## 项目结构

```
office-agent/
├─ backend/          # FastAPI 后端
│  ├─ app/
│  │  ├─ main.py             # 入口路由
│  │  ├─ schemas.py          # 请求/响应模型
│  │  ├─ utils.py            # 工具函数
│  │  ├─ services/           # 业务服务层
│  │  ├─ tools/              # Excel / Word 操作工具
│  │  └─ workflows/          # 业务流程编排
│  ├─ storage/
│  │  ├─ uploads/            # 上传文件目录
│  │  └─ outputs/            # 输出文件目录
│  ├─ requirements.txt
│  └─ run.py
├─ frontend/         # React + Vite 前端
│  ├─ index.html
│  ├─ package.json
│  └─ src/
│     ├─ App.jsx
│     └─ api.js
└─ README.md
```

## 快速启动

### 后端

```bash
cd backend
pip install -r requirements.txt
python run.py
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 任务执行方式

- 后端统一使用 `agent_autonomous` 模式执行任务（`/api/tasks/execute`）。
- 不再提供单独的 Excel+Word 专用工作流；上传文件后由 autonomous 工作流自动规划步骤。

### 使用独立浏览器环境（推荐）

为避免污染主浏览器（插件、Cookie、缓存、登录态），项目内提供了独立浏览器配置目录。

```bash
cd frontend
npm run browser:isolated
```

- 首次运行会在项目根目录创建 `.dev-browser-profile/`
- 该目录仅供本项目开发使用，可随时删除以重置浏览器环境
- 默认打开 `http://localhost:5173`
