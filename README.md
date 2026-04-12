# 代号：如果那时

> **如果那时，说了不同的话，结果是否不一样？**

大多数人在一段关系结束后的回望里，都曾被同一个问题击中过：  
**如果那一天，在那个关键节点，我说了另一句话，我们两个人的故事，会不会走向不同的结局？**

这个项目想做的，正是把这种迟来的反问，变成一次可以被认真推演的实验。它让用户回到某个**真实发生过的聊天时间点**，只改动自己说过的一句话，并在**绝不泄漏未来信息**的前提下，结合该节点之前已经发生的关系历史、话题脉络与互动状态，推演对方可能会如何回应，以及这段对话后续可能会如何分支发展。

它不是普通的聊天分析器，也不是单纯的“聊天对象复刻器”。  
它更接近一种**反事实对话模拟**：不是去宣称唯一正确的未来，而是尽可能还原“当时的那个人、当时的那段关系、当时的那个瞬间”，再去回答一个足够残酷、也足够动人的问题：

> **如果那时，真的换了一种说法，一切会不会不同？**

## 只启动后端

先确保你已经在项目根目录准备好了 `.venv`，并按需设置数据目录：

```powershell
cd D:\newProj
$env:IF_THEN_DATA_DIR = "D:\newProj\.data"
```

终端 1 启动 API：

```powershell
cd D:\newProj
.venv\Scripts\Activate.ps1
$env:IF_THEN_DATA_DIR = "D:\newProj\.data"
python scripts\run_api.py
```

终端 2 启动 worker：

```powershell
cd D:\newProj
.venv\Scripts\Activate.ps1
$env:IF_THEN_DATA_DIR = "D:\newProj\.data"
python scripts\run_worker.py
```

健康检查：

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/health"
```

## 只启动 Electron，快速体验前端页面

先确保根目录 `.venv` 已准备好，并且已经安装过桌面端依赖：

```powershell
cd D:\newProj\desktop
npm install
```

终端 A 启动 renderer dev server：

```powershell
cd D:\newProj\desktop
npm run dev
```

终端 B 构建 Electron 主进程并启动桌面端：

```powershell
cd D:\newProj\desktop
npm run build:electron
$env:IF_THEN_DESKTOP_RENDERER_URL = "http://127.0.0.1:5173"
npx electron .
```

说明：

- Electron 启动后会自动拉起 `python scripts/run_api.py`
- API 健康检查通过后会自动继续拉起 `python scripts/run_worker.py`
- 所以这里**不需要**你再手动提前启动后端
- 如果还没配置模型或导入会话，也可以先把桌面壳拉起来快速看前端页面
