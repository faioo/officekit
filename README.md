# officekit

OfficeKit 是一个面向办公自动化的小工具集合，自带现代化、高颜值的 Flet GUI 桌面客户端，并完美保留命令行 (CLI) 双模启动模式。

## 项目结构

```text
src/
└── officekit/
    ├── main.py
    ├── core/
    │   └── config.py
    ├── ui/
    │   ├── app.py          # GUI 主窗口布局
    │   ├── base.py         # GUI 统一二级子页面基类
    │   └── registry.py     # 统一工具注册表 (零入侵扩展)
    └── tools/
        ├── doi_query/
        │   ├── cli.py
        │   ├── core.py
        │   └── ui.py       # DOI 查询二级子页面
        └── word2img/
            ├── cli.py
            ├── core.py
            └── ui.py       # Word 转图片二级子页面
```

## 运行入口

安装 Python 依赖：

```bash
pip install -r requirements.txt
```

### 1. 启动 GUI 桌面客户端 (默认)

直接运行，即可打开跨平台图形桌面窗口：

```bash
PYTHONPATH=src python -m officekit.main
```

### 2. 启动 CLI 交互式命令行菜单

如果需要纯命令行运行，可以附加 `--cli` 参数：

```bash
PYTHONPATH=src python -m officekit.main --cli
```

### 3. 直接独立运行单个工具命令行

也可以直接运行各工具的独立 CLI：

```bash
PYTHONPATH=src python -m officekit.tools.word2img.cli path/to/document.docx -o output/images
PYTHONPATH=src python -m officekit.tools.doi_query.cli path/to/papers.xlsx -o output/with_doi.xlsx
```

## 功能组件说明

### 1. Word 转图片工具 (`word2img`)

利用系统底层工具链：先使用 LibreOffice 将 `.doc` 或 `.docx` 转换为临时 PDF，再使用 Poppler 的 `pdftoppm` 将 PDF 的每一页高精还原并导出为图片（支持 PNG、JPEG）。

需要提前在系统中安装以下工具命令：

- `soffice` 或 `libreoffice`
- `pdftoppm`

### 2. DOI 查询工具 (`doi_query`)

参考 [faioo/doi_tool](https://github.com/faioo/doi_tool/tree/main) 的处理方式：读取包含 `Title`、`Journal`、`Year` 列的 Excel 表格文件，批量检索 Crossref 数据库，追加 `DOI` 列（并完整保留 Excel 中的其他现有字段与格式）并另存为新文件。支持动态解析工作表（Worksheet）、自定义网络超时和查询延迟。

## 📦 桌面端可执行程序一键打包与分发 (面向普通非技术人员)

我们提供了一键打包脚本 `build_app.py`，能自适应生成最符合操作系统安全与启动性能的免环境独立程序：

### macOS 平台打包 (生成秒开的 `.app` 文件夹并压缩为 ZIP)
因为在 macOS 下如果将 windowed 界面打包为单文件 (onefile)，会导致 Gatekeeper 反复解压，出现严重的冷启动长延迟。因此我们的脚本会自动在 `dist/` 下生成标准的 `OfficeKit.app` 并将其压缩为 **`OfficeKit_macOS_v0.1.0.zip`**。
- **打包指令**：
  ```bash
  python build_app.py
  ```
- **分发与使用**：非技术人员在拿到导出的 ZIP 文件后，**双击解压**，直接将解压出的 `OfficeKit` (即 `OfficeKit.app`) **拖入“应用程序 (Applications)”文件夹**中，即可像普通苹果软件一样双击直接无门槛秒开运行！

### Windows 平台打包 (生成单个 `OfficeKit.exe` 文件)
在 Windows 下，脚本会自适应调用 PyInstaller 的单文件压缩机制，生成独立的 **`OfficeKit.exe`**。
- **打包指令**：
  ```bash
  python build_app.py
  ```
- **分发与使用**：直接将生成的 `OfficeKit.exe` 发送给普通用户，用户双击该 `.exe` 即可完美运行，无需安装任何环境。

---

## ⚙️ GitHub Actions 自动化 CI/CD 持续集成流水线

项目配置了强大的自动化 CI/CD Pipeline (详见 `.github/workflows/ci.yml`)，极大地规范了代码质量并解放了人工打包精力：

1. **持续集成 (CI - 跑测)**：每次有新的 Commit 推送 (Push) 到 `main` 分支或提交 Pull Request 时，Pipeline 会自动拉起 Ubuntu 环境，自动检查全部源码是否存在 Python 语法与编译错误，确保代码时刻健康。
2. **自动分发打包 (CD - Release 自动化发布)**：
   - 当你在本地通过 Git 触发版本 Tag 推送（例如 `git tag v0.1.0 && git push origin v0.1.0`）时，GitHub Pipeline 会自动通过 `matrix` 分别拉起 **macOS (macos-latest)** 和 **Windows (windows-latest)** 虚拟机运行打包工作。
   - 打包完成后，Pipeline 会自动将编译产物命名为带有具体版本号的文件（如 `OfficeKit_Windows_v0.1.0.exe` 和 `OfficeKit_macOS_v0.1.0.zip`）。
   - 最后，Pipeline 会调用 GitHub API 自动创建一个对应的 Release，并将这两个开箱即用的包作为 Release 的附件**自动发布**！非技术人员可以直接在 GitHub 的 "Releases" 栏目下一键下载最新版运行！

---

## 二次开发：如何扩展接入新工具

OfficeKit 的 GUI 采用**零入侵模块化设计**。如果你想新增一个“工具 C”：

1. **新建工具文件夹**：在 `src/officekit/tools/tool_c/` 下开发你的业务逻辑 `core.py`、命令行 `cli.py`。
2. **实现 GUI 子页面**：在同一个文件夹下创建 `ui.py`，新建一个类继承并实现 `BaseToolFrame`：
   ```python
   import flet as ft
   from officekit.ui.base import BaseToolFrame

   class ToolCFrame(BaseToolFrame):
       def build_ui(self) -> ft.Control:
           # 你的 UI 控件布局
           return ft.Column([ft.Text("这是新工具 C")])
   ```
3. **注册新工具**：打开 `[src/officekit/ui/registry.py](src/officekit/ui/registry.py)`，在 `REGISTERED_TOOLS` 中追加一项：
   ```python
   {
       "id": "tool_c",
       "name": "新工具 C",
       "icon": ft.Icons.AUTO_AWESOME_OUTLINED,
       "selected_icon": ft.Icons.AUTO_AWESOME,
       "class": ToolCFrame,
   }
   ```
   重启程序后，左侧导航栏将全自动增加该按钮，并动态支持子页面的状态留存和无缝切换！
