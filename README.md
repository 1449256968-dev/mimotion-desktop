# 小米运动桌面助手

**中文** | [English](README.en.md)

基于 [mimotion-run](https://github.com/xunichanghuan/mimotion-run) 修改的 Windows 桌面版。EXE 在自己的电脑上运行，填入账号、密码和步数，点击按钮即可操作，不用安装 Python、配置 GitHub Actions 或手写 JSON。

> 当前发行：`v1.0.0` · Windows x64 · 本地 EXE

[下载 EXE 与 SHA-256 校验文件](https://github.com/1449256968-dev/mimotion-desktop/releases/tag/v1.0.0)

## 使用

1. 从 Release 下载 **MiMotionDesktop.exe**，双击打开。
2. 输入小米运动账号（手机号或邮箱）和密码，点击 **验证登录**。
3. 填写最小、最大步数，点击 **提交步数**。想提交固定步数，两项填一样即可。
4. 查看窗口下方的日志，再到已绑定的微信或支付宝确认同步结果。

账号不是小米账号。第三方同步需要先在对应运动 App 中完成绑定。详细操作见 [INSTALL.md](INSTALL.md)。

程序在本机运行，但登录和提交步数需要联网，会直接请求上游运动服务。

## 本次更新

- 把原脚本改为中文图形界面，账号和步数直接填写。
- 增加登录验证、运行日志和取消按钮，网络请求在后台执行。
- 步数直接按输入范围随机生成，不再按时段缩放；最小值等于最大值时使用固定步数。
- 提供免安装单文件 EXE，可选记住账号和步数，不保存密码。

版本记录见 [CHANGELOG.md](CHANGELOG.md)。

## 已知限制

- 当前是手动、单账号版本，不包含定时任务和多账号批量提交。
- 上游接口、账号状态和第三方绑定会影响实际结果；接口提交成功不代表微信或支付宝已完成同步。
- 已完成 EXE 启动检查和 18 项离线测试，账号验证也已在本地使用中确认成功。离线测试使用模拟响应，不代表所有账号和第三方同步都已验证。
- 已发出的提交不能撤回。提交超时或断网时，先查看第三方步数，再决定是否重试；程序不会自动重试提交。

## 源码布局

| 路径 | 内容 |
|---|---|
| `desktop_app.py` | 桌面界面、后台任务、日志和本地设置 |
| `desktop_core.py` | 从上游改编的登录和步数提交逻辑 |
| `assets/` | 上游数据模板及程序图标 |
| `tests/` | 接口和界面的离线测试 |
| `build-desktop.ps1` | Windows EXE 构建脚本 |
| `tools/package-release.py` | 发行包、源码包与 SHA-256 校验文件 |
| `VERSION.json` | 当前发行版本及上游来源记录 |

源码运行、构建和校验方法见 [INSTALL.md](INSTALL.md)。

## 账号与隐私

密码只在内存中用于登录，不写入配置和运行日志。「记住账号与步数设置」默认关闭，开启后只在本机 `%LOCALAPPDATA%\MiMotionDesktop\settings.json` 保存账号和步数，取消勾选会删除该设置文件。

本仓库只包含筛选后的桌面版源码、文档和许可证，不包含个人账号配置、真实密码、访问令牌、运行日志、虚拟环境或原仓库的自动运行工作流。反馈问题时不要提交账号密码、令牌或未脱敏的截图，见 [SECURITY.md](SECURITY.md)。

## 来源与许可

原项目：[xunichanghuan/mimotion-run](https://github.com/xunichanghuan/mimotion-run)，原作者及贡献者保留原有权利。本版依据上游提交 [`f038d289cc58`](https://github.com/xunichanghuan/mimotion-run/commit/f038d289cc588e51ce357cb851302e0618f8c167) 改编，沿用 [Apache-2.0](LICENSE) 许可证。

本版新增图形界面、EXE 打包、输入校验、取消处理及离线测试，调整了步数选择和异常处理；登录协议和步数数据模板来源于原项目。具体修改说明见 [NOTICE.txt](NOTICE.txt)，依赖许可证见 [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt)。
