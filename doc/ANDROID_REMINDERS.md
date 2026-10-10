# SmartTodo 提醒与安卓打包

## 网站提醒

在“计划”页右上角的铃铛，或“工具箱 → 设置 → 任务提醒”打开提醒中心。

- 页面弹窗在登录后的所有页面运行，按任务的开始时间触发。
- 日计划以及指定执行日期的周、月、年计划均可提醒。无时间或已完成任务不提醒。
- 返回页面会补回当天未处理的提醒；刷新页面不会清空待处理列表。
- “5 分钟后”会保存延后时间；“本次不再提醒”只确认提醒，不会完成任务。
- 点击完成会写回账号；点击查看会进入对应日期、周期和任务编辑框。
- 提醒状态按账号、任务日期和开始时间隔离。
- 系统通知须用户授权。安卓浏览器通过 Service Worker 显示通知，桌面提供兼容路径。

普通浏览器的页面被系统暂停、关闭或锁屏时，不保证计时继续执行。Service Worker 本身不是后台闹钟，不会让关闭的页面持续计时。网站目前没有服务器 Web Push 订阅服务。

## WebToApp 原生接入

SmartTodo 检测 `window.NativeBridge.getScheduledNotificationVersion() === 1`，仅在完整适配的打包模板中启用后台定时通知。旧版模板不会错误地显示“后台提醒已就绪”。

使用**系统 WebView 内核**，开启“原生桥”及其中的“通知”和“定时通知”能力；不依赖旧的 Web Notification polyfill，也不需要悬浮窗权限。网页通知开关不能代替 Android 应用权限。

网页适配的接口：

```typescript
getScheduledNotificationVersion(): number // 当前协议为 1
replaceScheduledNotifications(namespace: string, payload: string): boolean
getNotificationPermissionState(): 'granted' | 'default' | 'denied'
requestNotificationPermission(): string
openNotificationSettings(): boolean
canScheduleExactAlarms(): boolean
openExactAlarmSettings(): boolean
scheduleNotification(payload: string): boolean
cancelAllNotifications(): boolean
```

`replaceScheduledNotifications` 的 namespace 为 `smarttodo`。payload 为 JSON 数组，每项包含 `tag`、`title`、`body`、`triggerAt`（毫秒）、`deepLink`、`channelId`、`playSound`。同一批次中不存在的旧任务必须取消，而不只是移除通知栏中的通知。返回 true 表示系统接受了安排，不代表用户一定看到了提示。

每次打开应用、本机修改计划和恢复到前台时，会刷新未来 7 天内最近的最多 500 项提醒；应用停留前台时也会定期更新。日期和开始时间使用手机的本地时间。每日任务由服务器展开为独立日期实例，再交给 Android AlarmManager，页面退出后仍可触发已安排的闹钟。

配套 WebToApp 源码修改包括：

- `BridgeNotificationScheduler.kt`：稳定 PendingIntent、批量替换、取消、持久保存和重启恢复。
- `NativeBridge.kt`：协议检测、批量安排、精确闹钟设置入口及真正取消定时闹钟。
- `BridgeAlarmReceiver.kt`：高优先级通知渠道、点击跳转任务、重启与授权后恢复。
- 宿主与 shell 清单同步接收闹钟广播。
- 导出及运行权限同步包含通知、精确闹钟、开机恢复与振动权限。

这些改动必须编译进 WebToApp 的 **shell 模板和打包器**。仅拉取 SmartTodo 镜像、更新网站，或继续用原先的 WebToApp APK 打包，都不会替换安卓原生代码。本地配套源码已修改；目前没有生成经过真机验收的新打包器或 APK。

## 重新构建打包器

在已配置兼容 JDK、Android SDK 和项目要求的 NDK 的 WebToApp 源码目录运行：

```powershell
.\gradlew.bat :shell:assembleRelease :app:syncShellTemplateApk --no-configuration-cache
.\gradlew.bat :app:testStandardDebugUnitTest --tests "*BridgeNotificationSchedulerTest" --tests "*RuntimePermissionSyncTest" -x syncCloneHostDex --no-configuration-cache
.\gradlew.bat :app:assembleStandardDebug -x syncCloneHostDex --no-configuration-cache
```

安装重新构建的打包器，再用它导出 SmartTodo APK。保持原签名才能覆盖安装已有的同包名应用。不要把旧的 shell 模板重新放回 assets。

本次本地验证：网页单元测试、类型检查和生产构建；浏览器真实通知接口与弹窗交互；安卓桥模拟的未来每日任务、延后和退出清理；打包配置字段一致性检查。安卓 Gradle 构建在启动时因缺少 Java 环境停止，因此安卓单元测试、模板编译及真机检查尚未完成。

## 手机验收

1. 安装新 APK，登录后进入“设置 → 任务提醒”，允许应用通知及“闹钟和提醒”权限。
2. 在手机通知设置中允许声音、横幅和锁屏通知；关闭会影响通知的勿扰设置。
3. 点击“测试提醒”，检查应用内弹窗和系统通知栏。
4. 新建两分钟后的任务，确认“后台定时提醒”已安排，然后返回手机桌面、锁屏，检查提醒和点击跳转。
5. 修改时间、完成、删除、延后任务，确认旧时间不再提醒。
6. 退出账号，确认旧账号的预约被清除；重新登录后重新安排。
7. 重新启动手机，检查已保存任务的恢复。

其他设备上的编辑要在本机联网同步后才能改变手机已有预约；离线超过 7 天需重新打开应用更新预约。Android 强行停止应用、关闭通知、撤销闹钟权限、厂商后台限制或勿扰模式，都可能阻止或延迟提示。系统决定锁屏及横幅的最终呈现；本项目不会强制覆盖其他应用显示全屏窗口。
