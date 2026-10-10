# 账号版 Docker 部署

## 当前状态

已实现数据库账号、注册登录、CSRF 验证、登录频率限制、个人设置、密码哈希与会话撤销。
数据库连接支持通过 `DATABASE_URL` 配置；数据库模型已通过 MySQL 建表语句编译检查。
本地预览与接口测试使用 SQLite。首尔服务器已通过宝塔创建独立的 `smarttodo` 数据库，
初始化 19 张表；生产容器已通过项目专用用户连接 MySQL，并验证账号、计划与附件的读写。

生产依赖独立保存在 `backend/requirements-production.txt`：PyMySQL 用于连接 MySQL，
Gunicorn 用于运行 Flask。生产镜像由 Node.js 24 构建前端，再使用 Python 3.12 运行账号版服务。
一个 worker 配合 8 个线程，避免重复启动应用内的定时任务；容器使用非 root 用户运行。

## 首次部署

在宝塔创建独立的 MySQL 数据库和专用用户，字符集使用 `utf8mb4`，应用只使用此库的权限。
然后在安装 Docker Compose 的 Linux 服务器上执行：

```sh
mkdir -p /www/wwwroot/smarttodo
cd /www/wwwroot/smarttodo
git clone https://github.com/Tompulsen/SmartTodo.git repository
cp repository/docker/compose.yaml compose.yaml
cp repository/docker/update.sh update.sh
cp repository/docker/.env.example .env
chmod 600 .env
mkdir -p data runtime-config
chown 10001:10001 data runtime-config
chmod 700 data runtime-config
```

填写 `.env` 中的数据库密码和随机会话密钥后，运行 `sh update.sh`。
容器仅监听 `127.0.0.1:18080`，通过 host 网络连接本机 MySQL。
宝塔站点反向代理到此端口，配置示例见 `docker/baota-proxy.conf`。站点须开启 HTTPS。
容器可在宝塔的 Docker 容器列表中管理，名称为 `smarttodo`。

## 版本更新与回退

每次推送 `main`，GitHub Actions 会测试代码、构建镜像并检查容器启动。
检查通过后发布 `ghcr.io/tompulsen/smarttodo:latest` 和 `sha-完整提交号` 两种标签。
首次发布后，须在 GitHub 的 Packages 设置中将此开源项目的容器包设为 Public，服务器才能匿名拉取。
当前 `ghcr.io/tompulsen/smarttodo` 已通过匿名镜像访问和服务器实际拉取验证。

在部署目录执行 `sh update.sh` 即可拉取镜像并更新容器；`sh update.sh source` 则拉取源码后本地构建。
GitHub 自动发布镜像，但不会自动替换服务器容器；服务器更新由部署管理员执行此脚本。
源码更新使用 `git pull --ff-only`，发现本地修改会停止，不会覆盖修改。
脚本等待新版本健康检查通过，失败时尝试恢复原镜像。
更新和回退都会根据 Compose 配置重新创建容器，以恢复网络等可能被面板改动的运行设置。
需要指定版本时修改 `.env` 中的 `SMARTTODO_IMAGE` 为已发布的 `sha-完整提交号` 标签后更新。
账号与任务保存在宝塔 MySQL 中，附件保存在 `data` 中，配置与会话密钥独立保存。
不要删除这些持久目录或使用删除数据卷的命令进行更新。
回退镜像不等于回退数据库；涉及数据库结构变更时，先备份并遵循该版本的迁移说明。

### 宝塔更新注意事项

优先通过部署目录的 `sh update.sh` 更新。未安装下述兼容处理时，不要使用容器详情中的通用「升级容器」功能替代项目更新脚本。
本项目依赖 `network_mode: host` 访问宝塔 MySQL；如果面板重新创建容器时改成 `bridge`，
容器内的 `127.0.0.1` 就不再是服务器，日志会出现 `Can't connect to MySQL server on '127.0.0.1'`。
Compose 配置、`.env`、数据目录和配置目录必须保留。host 网络下，宝塔端口映射显示 `--` 是正常的；
应用实际只监听服务器 `127.0.0.1:18080`，由网站反向代理对外提供 HTTPS。

如遇上述网络配置偏差，可在 `/www/wwwroot/smarttodo` 执行以下命令恢复，不删除数据库或挂载目录：

```sh
docker compose up -d --force-recreate --no-deps --pull never --wait --wait-timeout 120 smarttodo
docker inspect smarttodo --format '{{.HostConfig.NetworkMode}} {{.State.Health.Status}}'
```

预期结果为 `host healthy`，随后再使用项目更新脚本拉取新版本。

### 宝塔升级入口兼容

首尔面板当前版本的通用容器升级逻辑没有在创建容器时传入 `network_mode`，导致 host 容器变为 bridge。
`docker/install-baota-upgrade-guard.py` 为此版本提供一个仅针对 SmartTodo 的兼容处理：
容器名称与 Compose 项目均为 `smarttodo`，且执行的是升级操作时，调用部署目录的 `update.sh`，
保留 Compose 网络、挂载、权限及健康检查和失败回退行为。其他容器及普通编辑操作保持原逻辑。

管理员可在服务器执行：

```sh
cd /www/wwwroot/smarttodo
python3 repository/docker/install-baota-upgrade-guard.py --check
python3 repository/docker/install-baota-upgrade-guard.py
```

安装器先检查面板源码结构并备份原文件，再原子写入兼容处理；不匹配的面板版本会停止安装。
已安装时重复执行不会重复插入。安装后可在宝塔「升级容器」选择 SmartTodo 的已发布镜像标签。
宝塔自身升级可能覆盖这项兼容处理，面板更新后应重新执行 `--check`；项目更新脚本不受影响。
此处理不会放宽 MySQL 网络权限，也不会修改数据库连接地址或其他容器。

## 首尔部署验证

2026-10-10 已完成独立数据库、专用用户、19 张数据表、GitHub 源码部署与镜像发布。
宝塔站点 `todo.zaiduyu.top` 已创建，反向代理目标为 `http://127.0.0.1:18080`，代理缓存关闭。
站点反向代理配置保存在 `docker/baota-proxy.conf`，配置检查及 Nginx 重载通过。

生产容器名称为 `smarttodo`，镜像为 `ghcr.io/tompulsen/smarttodo:latest`，健康检查通过。
容器以 UID `10001` 运行，监听地址确认仅为 `127.0.0.1:18080`，中国时区正确。
部署目录为 `/www/wwwroot/smarttodo`，数据与配置分别挂载 `data` 和 `runtime-config`，
MySQL 由宝塔管理，不放入应用容器。原有服务保持健康。

已实际执行一次镜像拉取和容器替换，替换后验证原登录会话、日 / 周 / 月 / 年计划、
每日必做规则、任务时间段、跨宫格位置、个人设置与上传附件均保留。
公网注册、登录、密码修改、退出与账号数据隔离检查通过；电脑和手机页面检查未发现横向溢出。
35 项前端测试、57 项后端测试及 GitHub 容器启动检查通过。

用户已添加 `todo.zaiduyu.top` 的 DNS 记录。2026-10-10 查询两台 Cloudflare 权威 DNS，
均返回首尔源站 IP，当前观测为仅 DNS，尚未观测到橙云代理生效。
Cloudflare API 令牌的来源 IP 限制仍拒绝当前客户端，因此未通过 API 修改代理或 TLS 模式。

已通过宝塔签发并安装 Let's Encrypt HTTPS 证书，启用宝塔 ACME 自动续期和 HTTP 到 HTTPS 跳转。
公网请求验证：HTTP 返回 `301` 跳转至 HTTPS，HTTPS 证书校验通过；
登录、注册页面及 `/api/health` 返回 `200`，未登录的数据请求返回 `401`。
Nginx 配置检查通过，现有容器保持健康。Cloudflare 代理及其到源站的严格 TLS 校验仍待验证。
后端不可达时，站点返回 `503` 和 `no-store`，这不代表应用已经上线。

## 环境舒适度

环境舒适度使用已有账号与管理员权限，不需要新增密钥或生产依赖。启动时自动创建 `shared_location` 表，只保存各账号最新一条定位及对应的授权会话。更新前按常规备份数据库，现有计划数据不迁移。

服务器需要能够通过 HTTPS 访问 `api.open-meteo.com:443`。公网网页需要 HTTPS 和浏览器定位权限；不要在 Nginx 或代理响应中设置 `Permissions-Policy: geolocation=()`。管理员地图按需加载 OpenStreetMap，不会在用户打开天气页时加载地图。

位置授权与天气功能绑定，使用前展示明确说明；定位失败不放行。账号被停用、登录版本失效或定位会话结束后，管理接口不再提供该会话的位置。页面隐藏时暂停新定位，超过 90 秒显示最后位置、超过 30 分钟不再返回坐标。实际设备定位精度由浏览器/系统决定，不支持网页关闭后的持续后台定位。

## 配置变量

| 变量 | 用途 |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy 连接地址，默认 `sqlite:///data/data.db`；MySQL 形式为 `mysql+pymysql://用户:经URL编码的密码@127.0.0.1:3306/smarttodo?charset=utf8mb4` |
| `SMARTTODO_SECRET_KEY` | 至少 32 个字符的随机会话签名密钥；未设置时使用配置目录内持久化生成的密钥 |
| `SMARTTODO_LOCAL_MODE` | 服务器必须为 `0`；本机免登录启动器会设为 `1` |
| `SMARTTODO_REGISTRATION` | `1` 开放注册，`0` 关闭新注册，已有账号仍可登录 |
| `SMARTTODO_SECURE_COOKIE` | HTTPS 生产环境设为 `1`；本机 HTTP 预览设为 `0` |
| `SMARTTODO_TRUST_PROXY` | 只有应用仅能被可信反向代理访问时才设为 `1`，信任一层代理 |
| `SMARTTODO_ADMIN_USER` | 可选的首次管理员用户名，4–15 位字母、数字或下划线，字母开头 |
| `SMARTTODO_ADMIN_PASSWORD` | 与管理员用户名成对提供，至少 10 位；已有账号不会被自动覆盖或提权 |
| `SMARTTODO_SCHEDULER` | `1` 启用原有后台任务，`0` 关闭；测试中应关闭 |

数据库账号的密码应使用随机字符串，不能复用宝塔或服务器管理密码。
管理账号必须由上述初始化配置建立；公开注册始终得到普通账号。
首次初始化后可从运行环境移除管理员明文密码，登录校验使用数据库中的密码哈希。

## 文件与旧配置

- `/file/` 必须转发给后端进行账号检查，不能用 Nginx 的公共目录映射绕过权限。
- 服务器账号模式不自动访问用户提交的 URL，也不代用户下载远程文件，防止访问服务器内部网络。
- 用户可以上传本地附件，最大请求体为 8 MiB；上传文件以随机名称保存并作为附件下载。
- `config/default.json` 中的历史示例用户仅用于本机模式；服务器账号由 `account` 表管理。
- 不要直接公开已有本地数据库。需要保留历史数据时，先备份并明确旧数据所有者与新账号的对应关系。
