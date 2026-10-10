# SmartTodo

一个面向个人本地使用的待办、日程与专注工具。支持日 / 周 / 月 / 年计划、自定义任务宫格、可视化日程、番茄钟及循环播放的专注音频。

本项目基于 [LiZeC123/SmartTodo](https://github.com/LiZeC123/SmartTodo) 的 MIT 版本开发，保留原作者 LiZeC 的版权声明，并增加本地计划和专注体验。

## 功能

| 模块 | 功能 |
| --- | --- |
| 计划 | 日、周、月、年计划；编辑宫格主题；添加任务与事项；完成状态与备注 |
| 任务安排 | 开始 / 结束时间、每日必做、跨宫格拖动与优先级排序 |
| 视图 | 日时间轴、周视图、月历、年视图，以及任务表格展示 |
| 提醒 | 页面内到点提醒；在浏览器支持并授权时发送系统通知 |
| 专注 | 正计时、番茄钟、倒计时；关联计划；暂停与恢复；专注记录和每日目标 |
| 音频 | 八种内置合成环境音与旋律；本地音频导入、循环、音量和播放进度 |
| 原有工具 | 旧版番茄任务、便签、统计、打卡、体重记录与可选 AI 助手 |

## 本地运行

已在 Windows、Python 3.12、Node.js 24 环境验证。前端使用 Vue 3 + TypeScript + Vite，后端使用 Flask + SQLAlchemy + SQLite。

### 1. 获取源码并安装后端依赖

在 PowerShell 中运行：

```powershell
git clone https://github.com/Tompulsen/SmartTodo.git
cd SmartTodo
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

### 2. 构建前端

需要预先安装 Node.js 24 和 pnpm 11.25.0：

```powershell
cd web
pnpm install --frozen-lockfile
pnpm run build
cd ..
```

### 3. 启动

```powershell
.\Start-Local.ps1
```

默认地址为 <http://127.0.0.1:8080/index>，专注页为 <http://127.0.0.1:8080/tomato>。
如果端口被占用，启动脚本会查找相邻的可用端口，并打印实际地址。

也可以直接以前台方式运行：

```powershell
.\.venv\Scripts\python.exe scripts/serve-local.py --port 8080
```

macOS / Linux 可创建 `.venv`、安装同一依赖并构建前端，然后运行：

```sh
.venv/bin/python scripts/serve-local.py --port 8080
```

本地启动器仅监听 `127.0.0.1`，使用示例管理员作为数据所有者，不要求登录。
**不要把免登录本地服务转发到公网。** 普通后端部署仍保留原有登录流程；公开部署前必须自行配置账户、凭据及访问控制。示例账户 `admin` / `user` 的密码均为 `123456`，仅供本地演示与测试。

## 数据与配置

- 任务、计划和专注记录保存在运行时生成的 `data/data.db`。
- 个性化后端配置放在 `config/config.json`，覆盖示例 `config/default.json`。
- 本地音频保存在当前浏览器、当前站点的 IndexedDB 中，不上传到 GitHub，也不会自动在设备之间同步。
- 单个音频最大 50 MB，最多 20 首，总容量最大 200 MB。实际格式支持取决于浏览器。
- 刷新页面会保留音频库与播放偏好，但不会自动播放；离开专注页会停止背景音。
- 内置音频是合成环境音与旋律。发布版插图和提示音由项目脚本生成，不包含参考截图中的插画或个人媒体。

AI 助手是可选功能，需要在个人配置中填写兼容接口的信息。默认配置使用占位密钥。
本地启动器固定使用 `ENV=DEV`，不会执行生产环境中的自动 AI 记忆任务。

页面提醒依赖页面运行和浏览器权限。手机锁屏、关闭浏览器或系统暂停网页后，无法保证持续提醒或播放；此版本不包含后台推送服务。

## 开发与检查

```powershell
cd web
npm test
pnpm run type-check
pnpm run build
cd ..
```

后端计划与专注测试使用内存数据库：

```powershell
New-Item -ItemType Directory -Path data -Force
$env:PYTHONPATH = Join-Path $PWD 'backend'
.\.venv\Scripts\python.exe -m unittest app.tests.services.planner_test app.tests.services.period_planner_test app.tests.services.focus_test -v
```

GitHub Actions 会运行前端测试、类型检查、构建，以及上述后端测试。不会发布 Docker 镜像或调用外部 AI 服务。

## 目录

```text
backend/       Flask API、数据模型、业务逻辑与测试
web/           Vue 页面、组件、前端测试与静态资源
config/        不含真实凭据的默认示例配置
scripts/       本地启动器和素材生成脚本
docker/        上游容器部署文件
doc/           上游设计与使用文档
Start-Local.ps1 Windows 本地启动入口
```

`docker/` 保留了上游部署方案，容器模式不使用本地免登录启动器，且不在本版本的启动验证范围内。

## 许可与致谢

源码以 [MIT License](LICENSE) 开源，保留原作者 `Copyright (c) 2024 LiZeC`。
依赖及素材说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
