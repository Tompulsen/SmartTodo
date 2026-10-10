# SmartTodo

一个支持本机使用与独立账号的待办、日程与专注工具。支持日 / 周 / 月 / 年计划、自定义任务宫格、可视化日程、番茄钟及循环播放的专注音频。

本项目基于 [LiZeC123/SmartTodo](https://github.com/LiZeC123/SmartTodo) 的 MIT 版本开发，保留原作者 LiZeC 的版权声明，并增加本地计划和专注体验。

## 功能

| 模块 | 功能 |
| --- | --- |
| 计划 | 日、周、月、年计划；编辑宫格主题；添加任务与事项；完成状态与备注 |
| 任务安排 | 开始 / 结束时间、每日必做、跨宫格拖动与优先级排序 |
| 视图 | 日时间轴、周视图、月历、年视图，以及任务表格展示 |
| 提醒 | 全站到点弹窗、补回当天提醒、延后 5 分钟、提醒中心；授权后发送系统通知；配套 WebToApp 原生定时提醒接入 |
| 专注 | 正计时、番茄钟、倒计时；关联计划；暂停与恢复；专注记录和每日目标 |
| 音频 | 八种内置合成环境音与旋律；本地音频导入、循环、音量和播放进度 |
| 账号与设置 | 注册、登录、退出、修改昵称与密码；默认计划周期；账号数据隔离 |
| 待办关联 | 双方确认联系人、私聊、未读消息、分享今日计划快照、授权查看今日计划与撤回分享 |
| 环境舒适度 | 必须定位后使用；今日天气、体感、逐小时预报；使用期间管理员可查看最新上报位置 |
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
**不要把免登录本地服务转发到公网。** 本地示例配置中的 `admin` / `user` 只供免登录模式使用，不能在新的账号系统里直接登录。

### 注册与登录预览

在同一台电脑启动带账号功能的版本：

```powershell
.\.venv\Scripts\python.exe scripts/serve-local.py --accounts --port 8081
```

打开 <http://127.0.0.1:8081/register> 创建账号；登录后从工具箱进入设置。
账号模式不读取配置文件中的旧明文密码。密码以带随机盐的哈希保存，修改密码后所有设备的旧会话失效。
个人资料与日 / 周 / 月 / 年默认计划保存在账号中。计划、专注记录与任务附件按账号隔离；上传的专注音频仍保存在当前浏览器。
已有本地数据的用户名不能被公开注册领取；旧数据迁移需要由部署管理员单独安排。
此预览仅监听本机，仍是开发服务。正式 Docker 部署及配置变量见 [部署说明](doc/ACCOUNT_DEPLOYMENT.md)。

### 提醒与安卓打包

提醒与安卓打包的行为、权限设置及验证步骤见 [提醒与安卓打包](doc/ANDROID_REMINDERS.md)。安卓原生后台提醒需要配套修改后的 WebToApp 模板，旧 APK 仅更新网页不会自动获得此能力。

### 待办关联

登录账号后，从左侧「关联」或工具箱进入 `/connect`。输入对方的注册账号发送邀请，对方接受后即可聊天。
桌面端显示联系人、聊天和今日计划三栏；手机端可在联系人、对话和共享计划之间切换。

- 「分享今日计划」发送当前计划快照，默认不包含任务备注，可主动勾选包含备注，也可撤回分享。
- 为某位联系人开启「共享我的今日计划」后，对方可查看当天的任务、时间和完成状态，不含备注；双方的共享权限相互独立。
- 计划只读，联系人不能编辑你的任务。关闭共享或移除联系人后，后端立即拒绝相关访问。
- 页面在可见时每 5 秒更新消息、未读数和共享状态；聊天记录保存到数据库，支持读取更早消息。
- 移除联系人会同时清空双方的聊天记录。免登录本地模式不开放关联功能。

### 管理控制台

账号版的管理员在工具箱中可以看到「管理控制台」，地址为 `/tools/admin`。
支持搜索和分页查看用户、编辑昵称和默认计划、启用或停用账号、调整管理员角色、重置密码。
普通用户不会看到入口；后台逐次校验数据库中的角色，普通用户即使直接请求管理接口也会被拒绝。
管理员不能在控制台修改自己的账号，个人资料和密码从「设置」修改，避免误停用或移除最后一个管理员。
管理修改会使被编辑用户的旧登录失效；并发编辑使用版本校验，过期资料不会覆盖新修改。
账号管理不读取用户的私人计划和附件，也不自动迁移本地数据。
初始管理员由部署环境的 `SMARTTODO_ADMIN_USER` / `SMARTTODO_ADMIN_PASSWORD` 创建；不要将真实密码提交到仓库。

### 环境舒适度与位置

从工具箱进入 `/environment`。页面先说明定位用途以及管理员可查看的内容，点击「同意定位并使用」并允许浏览器定位后才能加载天气，没有单独的位置共享开关。拒绝定位时停留在入口，其他计划功能不受影响。

- 天气包含当前温度、体感、湿度、风速、今日降水概率、逐小时预报及日出日落，按所在地时区展示。舒适度是室外预报参考，并非室内传感器测量。
- 服务端通过 HTTPS 查询 Open-Meteo，只向天气服务提供保留两位小数的坐标；不向天气服务发送用户名。最多缓存 256 个区域，每个预报缓存 5 分钟。
- 账号模式下，使用期间向管理员共享设备上报的位置，页面保留可见提示。约每 30 秒请求一次新定位，位置变化时也会更新，上报间隔至少 10 秒；后台或锁屏可能暂停更新。
- 离开页面会停止设备定位并请求清空本次共享。断网或进程被系统直接终止时，清空请求可能无法送达；管理员会看到「最后位置」，超过 30 分钟不再返回坐标。数据库只保留最新一次位置，不保存轨迹。
- 管理控制台每 15 秒读取当前页用户的位置，显示坐标、设备精度及采集/接收时间；点击地图按钮后才向 OpenStreetMap 加载位置地图。普通用户无法调用位置管理接口。
- 浏览器的定位权限不能被网页绕过。公网需要 HTTPS；本机 `localhost` / `127.0.0.1` 可以测试。浏览器权限、设备定位精度和网页是否持续运行都会影响更新。
- 免登录本地模式同样需要定位来查询天气，但不向管理员上传位置。精确坐标不写入浏览器持久存储。

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

后端账号、计划与专注测试使用内存数据库：

```powershell
New-Item -ItemType Directory -Path data -Force
$env:PYTHONPATH = Join-Path $PWD 'backend'
.\.venv\Scripts\python.exe -m unittest app.tests.services.account_test app.tests.services.admin_test app.tests.services.connection_test app.tests.services.planner_test app.tests.services.period_planner_test app.tests.services.focus_test -v
```

GitHub Actions 会运行前端测试、类型检查、构建，以及上述后端测试。`main` 分支检查通过后，
会构建并实际启动验证容器，然后发布 `ghcr.io/tompulsen/smarttodo:latest` 和对应提交的版本标签。
不会调用外部 AI 服务。

## Docker 部署与更新

生产容器使用 Gunicorn 运行账号版应用，并通过 PyMySQL 连接独立 MySQL 数据库。
宝塔负责域名和 HTTPS，Compose 项目及容器名称均为 `smarttodo`。
2026-10-10 已验证首尔服务器上的容器运行、公网注册登录，以及实际镜像更新后的数据保留。
完整初始化步骤和配置变量见 [部署说明](doc/ACCOUNT_DEPLOYMENT.md)。

已部署服务器更新到仓库最新镜像：

```sh
cd /www/wwwroot/smarttodo
sh update.sh
```

也可以从 GitHub 拉取源码，在服务器本地构建：

```sh
cd /www/wwwroot/smarttodo
sh update.sh source
```

新版本通过健康检查才算更新成功；启动失败会尝试恢复原镜像。数据库、配置和附件均在容器外持久保存。
GitHub 会自动发布检查通过的镜像；服务器执行上述脚本后才会切换到新版本。
涉及数据库结构变更的版本应先在宝塔备份数据库，再按照该版本的迁移说明更新。

## 目录

```text
backend/       Flask API、数据模型、业务逻辑与测试
web/           Vue 页面、组件、前端测试与静态资源
config/        不含真实凭据的默认示例配置
scripts/       本地启动器和素材生成脚本
docker/        生产镜像、Compose、宝塔反代与更新脚本
doc/           上游设计与使用文档
Start-Local.ps1 Windows 本地启动入口
```

容器模式默认启用账号验证，不使用本地免登录启动器。MySQL 版本的 Compose 配置适用于 Linux 服务器。

## 许可与致谢

源码以 [MIT License](LICENSE) 开源，保留原作者 `Copyright (c) 2024 LiZeC`。
依赖及素材说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
