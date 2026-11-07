# 使用与构建

## 直接运行 EXE

适用于 Windows 10 / 11 64 位。

1. 打开 [Release](https://github.com/1449256968-dev/mimotion-desktop/releases/tag/v1.0.0)，下载 `MiMotionDesktop.exe`。也可下载 `mimotion-desktop-1.0.0-win64.zip` 后解压。
2. 双击 EXE，无需安装 Python，也不用注册 GitHub 或配置运行环境。
3. 输入小米运动账号和密码，点击「验证登录」。这一步不修改步数。
4. 输入步数范围后点击「提交步数」。范围内随机取一个整数；两个数字相同时提交固定步数。支持范围为 1～100000。
5. 在日志中查看结果，然后到已绑定的微信或支付宝检查同步。

程序在自己的电脑上运行，需要联网访问运动服务。请使用小米运动账号，不是小米账号。

## 设置与取消

「记住账号与步数设置」默认不选。开启后，只保存账号和步数，不保存密码；重新打开程序时需要再输入密码。

设置文件位于 `%LOCALAPPDATA%\MiMotionDesktop\settings.json`。取消勾选会删除已保存的设置。

取消会在网络请求之间生效，已经发出的请求不能撤回。等待当前请求返回后即可关闭窗口。提交超时、连接中断或返回异常时，服务端可能已经收到请求，请先检查第三方步数，再决定是否重试。

## 校验下载文件

Release 同时提供同名 `.sha256` 文件。在下载目录打开 PowerShell：

```powershell
Get-FileHash .\MiMotionDesktop.exe -Algorithm SHA256
Get-Content .\MiMotionDesktop.exe.sha256
```

两个哈希应一致。

## 从源码运行

安装 Python 3.13（包含 Tkinter），在源码目录执行：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
.\.venv\Scripts\python.exe desktop_app.py
```

运行离线测试，不会向真实账号提交数据：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 构建 EXE

在已安装依赖的源码目录执行：

```powershell
.\build-desktop.ps1
```

输出为 `dist\MiMotionDesktop.exe`。EXE 包含 Python 运行时、Tkinter、接口依赖、数据模板和许可证，使用者不需要另装运行环境。

在 Git 源码目录中生成发行包与源码包：

```powershell
.\.venv\Scripts\python.exe tools\package-release.py
```

输出位于 `release\`。源码包来自当前已提交的 Git 版本，发行包仅收录 EXE、文档和许可证；生成前需要提交源码修改。
