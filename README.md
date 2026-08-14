# 考研数学《880》智能拼好卷生成器

基于 Streamlit 的在线智能组卷工具。内置 1121 条题目元数据和 23 章 Markdown 正文，可按章节、题型、难度和专项标签进行无放回加权抽样，支持网页预览以及适配 GoodNotes 的两种 A4 PDF。

## 仓库结构

```text
.
├── .streamlit/config.toml       # Streamlit 主题与服务配置
├── data/
│   ├── metadata/                # 24 个 JSON 元数据文件
│   └── problems/                # 23 个章节 Markdown
├── scripts/package_data.py      # 本地数据重新归档与哈希校验脚本
├── app.py                       # Community Cloud 入口文件
├── data_loader.py               # 扫描、解析与 ID 关联
├── engine.py                    # 去重加权组卷引擎
├── pdf_exporter.py              # A4 PDF 与中文/LaTeX 排版
├── requirements.txt             # 云端 Python 运行依赖
├── requirements-dev.txt         # 本地测试依赖
└── packages.txt                 # 云端 Debian 系统包与中文字体
```

应用默认只读取仓库相对路径 `data/metadata` 和 `data/problems`，不依赖 Windows 盘符。环境变量 `MATH880_DATA_DIR`、`MATH880_CONTENT_DIR` 及本地 `config.toml` 仍可用于高级覆盖。

## 三步部署到 Streamlit Community Cloud

### 1. 推送到 GitHub

在 GitHub 新建一个空仓库，然后于项目根目录执行（替换用户名与仓库名）：

```bash
git add .
git commit -m "Deploy 880 smart paper generator"
git branch -M main
git remote add origin https://github.com/YOUR_NAME/YOUR_REPO.git
git push -u origin main
```

本目录已初始化为 Git 仓库；如果复制到别处后 `.git` 不存在，先执行 `git init`。

### 2. 创建云端应用

打开 [share.streamlit.io](https://share.streamlit.io)，使用 GitHub 登录，点击 **Create app** → **Yup, I have an app**，选择刚推送的仓库与 `main` 分支。

### 3. 一键 Deploy

入口文件填写 `app.py`。建议在 **Advanced settings** 选择 Python **3.12**，然后点击 **Deploy**。部署完成后会获得固定的 `*.streamlit.app` 地址，可直接在 iPad、手机和电脑访问。

Community Cloud 会自动读取：

- `requirements.txt`：安装锁定的 Python 包；
- `packages.txt`：安装 Pango、Cairo、GDK Pixbuf、libffi 和中文字体；
- `.streamlit/config.toml`：应用主题及服务器设置；
- `data/`：随仓库部署完整题库。

## PDF 与中文字体

- 云端优先使用 WeasyPrint；Linux 系统依赖由 `packages.txt` 自动安装。
- 字体回退顺序为 Noto Sans CJK SC、WenQuanYi Micro Hei、WenQuanYi Zen Hei、PingFang SC、Microsoft YaHei、sans-serif。
- LaTeX 在导出前转换为 MathML，选择/填空紧凑排版，解答题保留 120 mm 横线书写区。
- 纯享版只含题干；解析版在末尾附加已有答案、解析与踩坑提示。
- Windows 本地缺少 GTK/Pango 时，会自动回退到 Edge/Chrome 无头打印。

## 本地运行与测试

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
streamlit run app.py
```

浏览器访问 [http://localhost:8501](http://localhost:8501)。首次安装完成后，也可以双击 `启动应用.bat`。

```powershell
pytest -q
python -m compileall app.py data_loader.py engine.py pdf_exporter.py models.py config.py
```

## 重新归档本地题库

仓库已经包含当前完整数据。如源文件更新，可在 Windows 项目根目录执行：

```powershell
python scripts/package_data.py
```

也可以显式传入其他来源：

```powershell
python scripts/package_data.py --metadata-source "D:\你的元数据" --problems-source "D:\你的题目"
```

脚本复制后会逐文件校验 SHA-256，任何不一致都会立即停止并报错。

## 数据关联规则

加载器同时支持显式 ID（如 `01-基础-01`）与当前章节分组格式。对无 ID 的 Markdown，会按“章节 → 难度 → 题型 → 组内序号”与元数据确定性关联，并兼容 `**(1)**`、`1.`、`（1）` 三种题号。

> 当前 Markdown 主要包含题干和选项，没有独立的答案/详细解析分区；解析版会展示元数据中的踩坑分析，并对缺失内容明确标注。
