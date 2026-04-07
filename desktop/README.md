# Desktop Workspace

## 作用

`desktop/` 是 Electron 桌面壳工作区。当前阶段只负责：

- 启动 Electron 主进程与最小 renderer
- 自动拉起仓库根目录的 Python API / worker
- 通过 `GET http://127.0.0.1:8000/health` 轮询后端就绪状态
- 通过 preload bridge 把最小 boot-state 暴露给 renderer

## 开发前提

- 已在仓库根目录准备 Python 环境
- 推荐存在 `D:\newProj\.venv`
- 若未安装为 editable package，主进程会自动把 `src` 加入 `PYTHONPATH`
- 默认数据目录为项目根目录 `.data`；也可以自行设置 `IF_THEN_DATA_DIR`

## 常用命令

安装 Node 依赖：

```powershell
cd D:\newProj\desktop
npm install
```

启动 renderer dev server：

```powershell
cd D:\newProj\desktop
npm run dev
```

首次进入开发态，或修改了 `desktop/electron/*.ts` / `desktop/electron/**/*.ts` 之后，先生成 Electron 主进程与 preload 产物：

```powershell
cd D:\newProj\desktop
npm run build:electron
```

然后在另一个终端启动 Electron（连接 dev server）：

```powershell
cd D:\newProj\desktop
$env:IF_THEN_DESKTOP_RENDERER_URL = "http://127.0.0.1:5173"
npx electron .
```

构建并加载本地静态 renderer：

```powershell
cd D:\newProj\desktop
npm run build
npx electron .
```

`npm run build` 会同时生成：

- `dist/`：renderer 静态资源
- `dist-electron/electron/main.js` 与 `dist-electron/electron/preload.js`：Electron 主进程产物

开发态最小流程总结：

1. 终端 A：`npm run dev`
2. 终端 B：`npm run build:electron`
3. 终端 B：设置 `IF_THEN_DESKTOP_RENDERER_URL` 后执行 `npx electron .`

## Python 启动行为

Electron 主进程会按以下顺序启动：

1. 解析仓库根目录与 `.venv` Python（若存在）
2. 启动 `python scripts/run_api.py`
3. 轮询 `/health`
4. API 健康后启动 `python scripts/run_worker.py`

默认共享数据目录：

```text
D:\newProj\.data
```

若你在启动 Electron 前设置了 `IF_THEN_DATA_DIR`，主进程会沿用该目录。
