# manage_codex_sessions

独立的 Codex sessions 管理工具，支持：

- 查询活动 sessions
- GUI / Qt 管理 sessions
- session 改名
- 默认删除到回收站
- 从回收站恢复 / 清空回收站
- 按项目筛选和查看
- 打包为无需预装 Qt 的 Windows GUI 可执行文件

## 文件说明

- `manage_codex_sessions.py`：主程序，提供 CLI 和 GUI 逻辑
- `manage_codex_sessions_gui.py`：GUI 启动入口，适合直接打包 exe
- `build_manage_codex_sessions_gui.ps1`：Windows 一键打包脚本
- `.gitignore`：Python / PyInstaller 构建忽略规则

## 环境要求

- Windows
- Python 3.14+

GUI 依赖：

- `PySide6`

打包依赖：

- `PyInstaller`

## 安装依赖

只运行脚本：

```powershell
python -m pip install PySide6
```

如果要打包 exe：

```powershell
python -m pip install PySide6 pyinstaller
```

## CLI 用法

### 查询活动 sessions

```powershell
python manage_codex_sessions.py query
```

### 查询回收站

```powershell
python manage_codex_sessions.py trash
```

### 按项目统计

```powershell
python manage_codex_sessions.py projects
```

### 改名

```powershell
python manage_codex_sessions.py rename --id <session-id> --name "新名字"
```

### 删除到回收站

```powershell
python manage_codex_sessions.py delete --id <session-id> --yes
```

### 永久删除

```powershell
python manage_codex_sessions.py delete --id <session-id> --yes --permanent
```

### 恢复

```powershell
python manage_codex_sessions.py restore --id <session-id> --yes
```

### 清空回收站

```powershell
python manage_codex_sessions.py empty-trash --all --yes
```

## GUI 用法

启动 GUI：

```powershell
python manage_codex_sessions.py gui
```

或者：

```powershell
python manage_codex_sessions_gui.py
```

GUI 支持：

- 活动 sessions / 回收站 双页签
- 单选 / 多选 / 全选
- 双击 `Thread` 弹出重命名对话框
- 删除到回收站
- 从回收站恢复
- 清空回收站
- 按项目筛选
- 单实例运行

## 打包为 Windows exe

默认打成单文件 GUI exe：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_manage_codex_sessions_gui.ps1
```

跳过依赖安装：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_manage_codex_sessions_gui.ps1 -SkipDependencyInstall
```

打成目录模式：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_manage_codex_sessions_gui.ps1 -OneDir -SkipDependencyInstall
```

输出产物：

- `dist\manage_codex_sessions_gui.exe`
- 或 `dist\manage_codex_sessions_gui\`

## 数据位置

默认读取当前用户的：

- `~/.codex/session_index.jsonl`
- `~/.codex/sessions/`
- `~/.codex/session_trash/`

也可以通过 `--codex-home` 指定其他 Codex 数据目录。
