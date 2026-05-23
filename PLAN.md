# 2D 转 3D 子功能详细规划

## 1. 项目定位

本项目是一个更大系统中的小功能模块，不追求复杂前端和完整产品化体验，核心目标是把 2D 文件转换成可用的 3D 模型文件。

首版目标：

- 输入：`.webp`、`.jpg`、`.png`、`.svg`、`.pdf`
- 输出：`.obj`、`.3mf`
- 运行环境：Windows 本机
- 使用方式：本地 Web API + 一个简陋测试前端
- 主要用途：
  - 生成可预览的 3D 模型
  - 导出 OBJ 给通用 3D 软件使用
  - 导出 3MF 给 Bambu Studio / 3D 打印流程使用

首版不做：

- 精致前端
- 用户系统
- 多用户任务队列
- 云端 GPU 服务
- 自动发送到打印机
- 生产级部署
- 完整商业许可证审计

## 2. 总体架构

### 2.1 技术栈

后端：

- Python 3.11
- FastAPI
- Uvicorn
- Pillow
- trimesh
- numpy
- pydantic
- image-to-3D 模型 backend

前端：

- 最简 HTML / Vite / React 均可
- 不做设计系统
- 只保留上传、状态显示、下载和简单预览

3D 预览：

- Three.js
- 内部使用 `preview.glb` 作为浏览器预览格式

文件导出：

- OBJ
- 3MF
- 内部 GLB 仅用于预览

## 3. 推荐目录结构

```text
E:\2Dto3D
├── PLAN.md
├── README.md
├── backend
│   ├── app
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api
│   │   │   ├── jobs.py
│   │   │   └── system.py
│   │   ├── core
│   │   │   ├── input_processor.py
│   │   │   ├── generator.py
│   │   │   ├── mesh_processor.py
│   │   │   ├── exporter.py
│   │   │   ├── bambu.py
│   │   │   └── job_store.py
│   │   └── models
│   │       ├── job.py
│   │       └── system.py
│   ├── requirements.txt
│   └── run.py
├── frontend
│   ├── index.html
│   ├── package.json
│   └── src
│       └── main.ts
├── data
│   └── jobs
│       └── {job_id}
│           ├── input_original
│           ├── input.png
│           ├── preview.glb
│           ├── output.obj
│           ├── output.mtl
│           ├── texture.png
│           ├── output.3mf
│           ├── status.json
│           └── log.txt
└── models
    └── local_backend
```

## 4. 核心流程

### 4.1 上传文件

用户通过测试前端或 API 上传文件。

支持格式：

- `.webp`
- `.jpg`
- `.jpeg`
- `.png`
- `.svg`
- `.pdf`

上传后创建一个 job：

```text
data/jobs/{job_id}
```

保存原始文件和任务状态。

### 4.2 输入预处理

所有输入最终统一转换成标准 PNG。

图片文件：

- `.webp/.jpg/.png` 直接读取
- 转换为 RGBA PNG
- 统一尺寸
- 可选背景移除
- 可选主体裁剪

SVG 文件：

- 先 rasterize 成 PNG
- 再进入图片流程

PDF 文件：

- 首版只支持单页
- 默认第 1 页
- 用户可以传 `pdf_page`
- 将指定页面渲染成 PNG
- 再进入图片流程

首版不做 PDF 多页批处理。

## 5. 3D 生成策略

### 5.1 本地 backend

首版以本地模型为主。

推荐优先级：

1. SF3D 类模型
   - 更适合生成带纹理/UV 的模型
   - 更适合渲染模式
2. TripoSR
   - 作为 fallback
   - 更适合先跑通几何生成
3. Hunyuan3D / TRELLIS
   - 后续作为高质量 backend 评估
   - 不作为首版硬依赖

### 5.2 云端 backend

首版只预留接口：

```text
backend=cloud_stub
```

如果用户选择云端 backend，返回明确错误：

```json
{
  "code": "CLOUD_BACKEND_NOT_CONFIGURED",
  "message": "Cloud backend is reserved but not configured in MVP."
}
```

后续可以接入：

- 自托管 GPU 服务
- 第三方 image-to-3D API
- 局域网推理服务器

## 6. Mesh 处理

生成模型后统一进入 mesh 处理模块。

打印模式 `print`：

- 修复法线
- 删除重复顶点
- 删除退化面
- 尝试修复非流形边
- 尝试封闭网格
- 统一单位为毫米
- 模型居中
- 模型底部落到 Z=0
- 检查尺寸是否过大或过小
- 检查是否存在明显薄壁问题

渲染模式 `render`：

- 尽量保留 UV
- 尽量保留纹理
- 尽量保留材质
- 不强制封闭模型
- 优先视觉效果

## 7. 输出格式

### 7.1 OBJ

OBJ 用于通用 3D 软件。

渲染模式下推荐打包：

```text
model.zip
├── output.obj
├── output.mtl
└── texture.png
```

打印模式下可以只导出几何 OBJ。

### 7.2 3MF

3MF 是 Bambu Studio 和 3D 打印的主要格式。

要求：

- 单位使用毫米
- 模型坐标合理
- 模型居中
- 底部贴近打印平台
- 尽量保证网格可打印

### 7.3 GLB

GLB 只作为网页预览格式。

首版不承诺对外导出 GLB。

## 8. Bambu Studio 集成

### 8.1 首版目标

首版做轻量接入：

- 生成 Bambu Studio 可打开的 `.3mf`
- 提供一个“打开 Bambu Studio”按钮
- 后端调用本机 Bambu Studio 打开生成文件

用户仍然在 Bambu Studio 中完成：

- 选择打印机
- 选择耗材
- 设置支撑
- 切片
- 发送打印

### 8.2 Bambu Studio 路径检测

后端检测常见安装路径：

```text
C:\Program Files\Bambu Studio\bambu-studio.exe
C:\Program Files\Bambu Studio\BambuStudio.exe
C:\Users\{user}\AppData\Local\Programs\Bambu Studio\BambuStudio.exe
```

如果找不到，返回明确错误，并提示用户手动打开 3MF。

### 8.3 第二阶段能力

后续可调用 Bambu Studio CLI：

- 自动打开项目
- 自动摆盘
- 自动朝向
- 自动切片
- 导出 Bambu 项目 3MF

第二阶段仍不建议直接做自动发送到打印机。

## 9. API 设计

### 9.1 创建任务

```http
POST /api/jobs
```

请求：

- `file`: 上传文件
- `profile`: `print` 或 `render`
- `backend`: `local` 或 `cloud_stub`
- `pdf_page`: PDF 页码，默认 `1`

返回：

```json
{
  "job_id": "string",
  "status": "queued"
}
```

### 9.2 查询任务

```http
GET /api/jobs/{job_id}
```

返回：

```json
{
  "job_id": "string",
  "status": "queued|preprocessing|generating|processing_mesh|exporting|done|failed",
  "progress": 0.5,
  "error": null,
  "outputs": {
    "obj": true,
    "3mf": true,
    "preview": true
  }
}
```

### 9.3 下载模型

```http
GET /api/jobs/{job_id}/download?format=obj
GET /api/jobs/{job_id}/download?format=3mf
```

### 9.4 获取预览模型

```http
GET /api/jobs/{job_id}/preview
```

返回：

```text
preview.glb
```

### 9.5 打开 Bambu Studio

```http
POST /api/jobs/{job_id}/open-bambu
```

行为：

- 检查 `output.3mf` 是否存在
- 检查 Bambu Studio 是否安装
- 调用 Bambu Studio 打开 3MF

失败返回：

```json
{
  "code": "BAMBU_STUDIO_NOT_FOUND",
  "message": "Bambu Studio was not found. Please open the 3MF manually."
}
```

### 9.6 系统检查

```http
GET /api/system/check
```

返回：

```json
{
  "python": true,
  "gpu": true,
  "cuda": true,
  "local_model": false,
  "bambu_studio": false
}
```

## 10. 最简前端

前端只做调试页。

页面元素：

- 文件上传 input
- PDF 页码 input
- 模式选择：
  - print
  - render
- backend 选择：
  - local
  - cloud_stub
- 上传/生成按钮
- 状态文本
- 进度文本
- 简单 Three.js 预览区域
- 下载 OBJ 按钮
- 下载 3MF 按钮
- 打开 Bambu Studio 按钮

不做：

- 精致布局
- 动画
- 登录
- 多任务历史
- 响应式细节
- 复杂组件库

## 11. 任务状态设计

状态枚举：

```text
queued
preprocessing
generating
processing_mesh
exporting
done
failed
```

每个 job 保存：

```json
{
  "job_id": "string",
  "status": "generating",
  "progress": 0.4,
  "created_at": "datetime",
  "updated_at": "datetime",
  "profile": "print",
  "backend": "local",
  "input_file": "input_original",
  "error": null
}
```

## 12. 错误处理

常见错误码：

```text
UNSUPPORTED_FILE_TYPE
PDF_RENDER_FAILED
SVG_RENDER_FAILED
IMAGE_PREPROCESS_FAILED
LOCAL_MODEL_NOT_FOUND
GPU_OUT_OF_MEMORY
GENERATION_FAILED
MESH_PROCESS_FAILED
EXPORT_OBJ_FAILED
EXPORT_3MF_FAILED
BAMBU_STUDIO_NOT_FOUND
CLOUD_BACKEND_NOT_CONFIGURED
```

错误信息要求：

- 前端能直接显示
- log 文件保留详细 traceback
- API 返回简洁错误

## 13. 测试计划

### 13.1 输入测试

测试文件：

- PNG
- JPG
- WEBP
- SVG
- PDF 单页
- PDF 多页但只选一页

验证：

- 能生成 `input.png`
- 尺寸合理
- 透明通道合理
- 错误输入能返回明确错误

### 13.2 API 测试

验证：

- 能创建任务
- 能查询任务状态
- 失败状态可读
- 完成后能下载 OBJ
- 完成后能下载 3MF
- 缺文件时返回 404 或明确错误

### 13.3 Mesh 测试

验证：

- 顶点数大于 0
- 面数大于 0
- bbox 尺寸合理
- 打印模式下底部 Z 接近 0
- 模型中心接近原点
- 3MF 可重新读取

### 13.4 Bambu Studio 测试

验证：

- 3MF 可手动打开
- 安装 Bambu Studio 时按钮可打开
- 未安装时返回明确错误
- Bambu Studio 中模型尺寸合理

### 13.5 前端测试

验证：

- 能上传
- 能显示状态
- 能显示失败原因
- 能下载文件
- 能预览 GLB
- 按钮不会在任务未完成时误触发

## 14. 里程碑

### M1：项目骨架

目标：

- 建立后端 FastAPI
- 建立最简前端
- 建立 `data/jobs` 结构
- 实现系统检查 API

产物：

- 后端能启动
- 前端能打开
- `/api/system/check` 可用

### M2：输入处理

目标：

- 支持 PNG/JPG/WEBP
- 支持 SVG 转 PNG
- 支持 PDF 单页转 PNG

产物：

- 任意支持输入都能生成 `input.png`

### M3：任务系统

目标：

- 创建 job
- 保存状态
- 查询状态
- 保存错误日志

产物：

- `POST /api/jobs`
- `GET /api/jobs/{id}`

### M4：本地 3D 生成

目标：

- 接入第一个本地 image-to-3D backend
- 从 `input.png` 生成 mesh

产物：

- 能生成初始 3D 模型文件

### M5：Mesh 处理和导出

目标：

- 实现 print/render profile
- 导出 OBJ
- 导出 3MF
- 生成 preview GLB

产物：

- `output.obj`
- `output.3mf`
- `preview.glb`

### M6：前端调试页

目标：

- 上传
- 状态轮询
- 简单预览
- 下载 OBJ/3MF

产物：

- 一个能完整跑通流程的简陋页面

### M7：Bambu Studio 集成

目标：

- 检测 Bambu Studio
- 打开生成的 3MF
- 增加基础打印预检

产物：

- `POST /api/jobs/{id}/open-bambu`
- Bambu Studio 可打开模型

### M8：稳定性整理

目标：

- 错误码整理
- README
- 依赖说明
- 样例输入
- 基础测试

产物：

- 项目可交给后续大系统集成

## 15. 开发优先级

最高优先级：

1. 输入统一成 PNG
2. 本地 image-to-3D 跑通
3. OBJ/3MF 导出
4. Bambu Studio 能打开 3MF

中优先级：

1. 网格修复
2. 打印模式预检
3. 简单 GLB 预览
4. 错误处理

低优先级：

1. 好看的前端
2. 多任务历史
3. 云端 backend
4. 自动切片
5. 自动发送打印

## 16. 关键假设

- `.obg` 视为 `.obj` 的笔误。
- 首版运行在 Windows 本机。
- 当前机器有 NVIDIA RTX 5060 Laptop 8GB 显存。
- 输入主要是单个主体图片。
- 前端只是调试入口，后续可以被主系统替换。
- 首版默认非商用探索。
- 后续商用前需要重新检查模型、依赖和素材许可证。
- Bambu Studio 集成首版只做到“打开 3MF”，不自动发送打印。
