# manage_codex_sessions

[![Python](https://img.shields.io/badge/python-3.14%2B-blue.svg)](./README.md)
[![Platforms](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-2ea44f.svg)](./README.md)
[![GUI](https://img.shields.io/badge/GUI-PySide6-41CD52.svg)](./README.md)
[![Build](https://img.shields.io/badge/build-PyInstaller-f97316.svg)](./README.md)

[English](./README.md) | 简体中文

`manage_codex_sessions` 是一个用于浏览和管理本地 Codex sessions 的独立工具。
它同时提供 CLI 和 Qt GUI，可用于查看活动 sessions、查看回收站、重命名线程、默认安全删除到回收站、恢复已删除 session，以及打包 GUI 为可分发应用。

## 功能亮点

- 在一个工具中同时查看活动 sessions 和回收站 sessions。
- 既支持 CLI 改名，也支持在 GUI 中双击 `Thread` 列重命名。
- 默认删除到回收站，之后可恢复或永久清理。
- 支持按项目、工作目录、标题、来源等条件筛选。
- 支持按项目汇总 sessions，便于集中清理。
- CLI 支持通过 `--lang` 或 `CODEX_LANG` 在中英文之间切换。
- GUI 支持中英文界面，可自动跟随系统语言，也可手动切换。
- 自带 PyInstaller 脚本，可为 Windows、macOS、Linux 构建 GUI 产物。

## 项目结构

- `manage_codex_sessions.py` —— 主 CLI 入口，同时包含共享 GUI 逻辑。
- `manage_codex_sessions_gui.py` —— 精简 GUI 启动入口，适合直接打包。
- `build_manage_codex_sessions_gui.py` —— 跨平台 PyInstaller 构建脚本。
- `build_manage_codex_sessions_gui.ps1` —— 面向 Windows 用户的 PowerShell 包装脚本。
- `requirements-build.txt` —— 构建阶段依赖清单。

## 环境要求

- Python `3.14+`
- Windows、macOS 或 Linux

可选依赖：

- `PySide6`：GUI 运行所需
- `PyInstaller`：打包所需

## 安装

只安装 GUI 运行依赖：

```bash
python -m pip install PySide6
```

如果还需要打包：

```bash
python -m pip install -r requirements-build.txt
```

## CLI 快速开始

查看活动 sessions：

```bash
python manage_codex_sessions.py query
```

手动指定 CLI 语言：

```bash
python manage_codex_sessions.py query --lang en
python manage_codex_sessions.py query --lang zh-CN
```

查看回收站 sessions：

```bash
python manage_codex_sessions.py trash
```

按项目汇总 sessions：

```bash
python manage_codex_sessions.py projects
```

重命名 session：

```bash
python manage_codex_sessions.py rename --id <session-id> --name "新的 session 名称"
```

将 session 移入回收站：

```bash
python manage_codex_sessions.py delete --id <session-id> --yes
```

永久删除全部活动 sessions：

```bash
python manage_codex_sessions.py delete-all --yes --permanent
```

从回收站恢复 session：

```bash
python manage_codex_sessions.py restore --id <session-id> --yes
```

清空整个回收站：

```bash
python manage_codex_sessions.py empty-trash --all --yes
```

启动 GUI：

```bash
python manage_codex_sessions.py gui
```

手动指定 GUI 语言：

```bash
python manage_codex_sessions.py gui --lang en
python manage_codex_sessions.py gui --lang zh-CN
```

或者直接运行专用 GUI 入口：

```bash
python manage_codex_sessions_gui.py
```

也可以通过 `CODEX_LANG=en` 或 `CODEX_LANG=zh-CN` 同时控制 CLI 和 GUI 语言。
如果只想覆盖 GUI 语言，可在启动前设置 `CODEX_UI_LANG=en` 或 `CODEX_UI_LANG=zh-CN`。

## GUI 功能

- 活动 sessions / 回收站双标签页。
- 支持单选、多选、全选。
- 支持项目筛选和全文搜索。
- 双击 `Thread` 列即可进入重命名流程。
- 支持恢复、永久删除、批量删除等操作。
- 支持 CLI 中英文输出。
- 支持英文和简体中文界面。
- 带单实例锁，避免重复打开多个 GUI 窗口。

## 跨平台构建

构建单文件 GUI 产物：

```bash
python build_manage_codex_sessions_gui.py
```

跳过依赖安装：

```bash
python build_manage_codex_sessions_gui.py --skip-dependency-install
```

构建目录版产物：

```bash
python build_manage_codex_sessions_gui.py --onedir --skip-dependency-install
```

向 PyInstaller 透传额外参数：

```bash
python build_manage_codex_sessions_gui.py -- --icon app.ico
```

## Release 自动化

推送新的 Git tag 后，GitHub Actions 会自动构建 Windows、macOS、Linux 三个平台的发布产物，并发布到 GitHub Release：

```bash
git tag v1.0.0
git push origin v1.0.0
```

其中 Windows 产物会打包为 `.zip`，Linux 和 macOS 产物会打包为 `.tar.gz`。

## Windows PowerShell 快捷用法

构建单文件产物：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_manage_codex_sessions_gui.ps1
```

跳过依赖安装：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_manage_codex_sessions_gui.ps1 -SkipDependencyInstall
```

构建目录版产物：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_manage_codex_sessions_gui.ps1 -OneDir -SkipDependencyInstall
```

常见输出位置：

- Windows：`dist\manage_codex_sessions_gui.exe` 或 `dist\manage_codex_sessions_gui\`
- Linux：`dist/manage_codex_sessions_gui` 或 `dist/manage_codex_sessions_gui/`
- macOS：`dist/manage_codex_sessions_gui` 或 `dist/manage_codex_sessions_gui.app`

## 数据目录

默认读取当前用户的 Codex 数据目录：

- `~/.codex/session_index.jsonl`
- `~/.codex/sessions/`
- `~/.codex/session_trash/`

也可以通过 `--codex-home` 指定其他 Codex 数据目录。
