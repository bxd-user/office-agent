# Office Agent

> 基于 AI 的 Office 自动化工具：从 Excel 数据批量填充 Word 模板，一键生成多份文档。

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
