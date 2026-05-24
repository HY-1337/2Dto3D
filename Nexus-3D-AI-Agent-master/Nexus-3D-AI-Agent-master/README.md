# 🌟 Nexus 3D: 终极全链路 3D 创世数字人系统

**Nexus 3D** 是一个极其强大的端到端（End-to-End）全自动化工作流平台。只需一句提示词，即可实现从 AI 原画设计、3D 模型生成、无头格式转换、Unity 自动装配动作，一直到操控现实生活中的 Bambu (拓竹) 3D 打印机打印实体，同时赋予虚拟模型 DeepSeek 大脑与 GPT-SoVITS 语音克隆的灵魂！

## 🏗️ 核心 6 步流水线架构

1. **AI 生成 2D 图像**：输入文本，调用大语言视觉模型生成 2D 设定图。
2. **2D 转 3D 建模**：通过图生 3D 技术，将 2D 图像挤压为高精度全景 3D 网格模型 (`.glb`)。
3. **格式化与装配**：后台静默调用 Blender，将模型转为游戏标准的 `.fbx` 格式，并自动放入 Unity 项目。
4. **现实降临 (3D 打印)**：自动调用 Bambu Studio 切片为 `.gcode`，并通过局域网直接推送到 Bambu 打印机。
5. **AI 动作生成与绑定**：在 Unity 内为模型套用 Animator 状态机，根据对话意图自动播放动作。
6. **克隆声音与问答大脑**：双轨运行 Python WebSocket 服务，接入 DeepSeek 大脑与本地 GPT-SoVITS 进行实时语音互动！

---

## 🚀 快速开始 (Quick Start)

### 环境准备 (Prerequisites)
* **Python 3.10+** (用于后端 `backend2`)
* **Node.js** (用于前端 `frontend2`)
* **Unity Editor 2022+** (用于打开 `chaoliu2` 项目)
* **Blender** (需将执行路径添加至环境变量或运行时指定)
* **Bambu Studio** (如果你需要实体 3D 打印功能)
* **API Keys 准备**：
  * `TRIPO_API_KEY`: 用于图生 3D 模型生成。
  * `OPENAI_API_KEY` / `DEEPSEEK_API_KEY`: 用于接入数字人大脑。
  * `GPT-SoVITS`: 需在本地启动 API 推理服务 (默认端口 `9880`)。

### 步骤 1：启动数字人大脑 (后端服务器)
这会开启 WebSocket 通讯通道，负责处理前端指令、DeepSeek 意图识别和 GPT-SoVITS 语音合成。
```bash
cd backend2
pip install -r requirements.txt  # 安装相关依赖 (如果有)
export OPENAI_API_KEY="your-deepseek-key"
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
python interactive_server.py
```
> **提示**：看到 `server listening on 127.0.0.1:8765` 表示大脑已经上线待命！

### 步骤 2：启动控制面板 (前端界面)
这是你的指挥中心，支持文件拖拽、Pipeline 监控和数字人实时语音文字沟通。
```bash
cd frontend2
npm install
npm run dev
```
打开浏览器访问 `http://localhost:5173`。

### 步骤 3：运行 3D 创世主程序
当你需要在本地从零生成一个 3D 角色时，在终端运行强大的 6 步流水线主程序：
```bash
cd backend2
export TRIPO_API_KEY="your-tripo-api-key"

# 运行全链路指令 (包含 3D 打印)
python main.py \
  --prompt "A detailed 3D model of a cyber ninja character, humanoid" \
  --unity-path "C:\Users\Asus\chaoliu2" \
  --printer-ip "192.168.1.10" \
  --printer-code "12345678"
```
*注：如果不写打印机 IP 参数，则自动跳过实体打印步骤。*

### 步骤 4：在 Unity 中注入灵魂
1. 打开 Unity，加载 `chaoliu2` 项目。
2. 点击顶部菜单栏 **Nexus 3D -> 一键自动配置数字人**。刚才生成的 `.fbx` 模型会瞬间出现在场景中央，并被自动挂载好所有神经代码 (`AvatarController`)。
3. 点击 **Play (▶️)** 开始运行游戏。

### 步骤 5：跨次元互动！
回到你的前端网页：
1. 确保右侧面板出现 `🟢 Connected to AI Interactive Server.`
2. 可以在 **Voice Cloning (GPT-SoVITS)** 模块中跳转到原生界面配置好你想要克隆的声纹。
3. 在左下角 **Interact with Unity Avatar** 聊天框中输入：“你好！请跟我招招手并做个自我介绍！”
4. 观看奇迹：Unity 中的模型会**自动挥手**，并用你**克隆的声音**亲切地回应你！

---

## 目录结构说明

* `/backend2/`: Python 大脑中枢与 3D 生成核心。
  * `main.py`: 流水线控制器。
  * `interactive_server.py`: 数字人大脑与通信引擎。
  * `agent_tools.py` & `image_generator.py` & `bambu_tool.py`: 各模块能力组件。
* `/frontend2/`: React 监控与交互面板。
* `/chaoliu2/`: Unity 游戏客户端与数字人渲染端。
