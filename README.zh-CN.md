# siyuan-cli-skill

[![CI](https://github.com/betterLitao/siyuan-cli-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/betterLitao/siyuan-cli-skill/actions/workflows/ci.yml)
[English](README.md)

![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-6f42c1.svg)

一个可复用的多文件 skill，也可以单独当成 CLI 使用，用来稳定地读写思源文档。

它把 Siyuan Kernel API 包装成一个 Python CLI，这样助手和自动化脚本就不用再手搓常见文档操作的请求体。

## 演示

![Siyuan CLI config demo](assets/demo-config.svg)

## 特性

- 所有命令统一输出结构化 JSON
- 提供 `config --doctor` 用来排查配置来源和缺失项
- 支持配置文件回退，避免换个 shell 就丢环境变量
- 默认 notebook 模型通用化为 `default_notebook` 和 `purpose_notebooks`
- 保留 `SIYUAN_LEARN_NOTEBOOKS` 作为旧配置兼容层
- 支持 read、search、update、append、create、delete 文档操作
- `replace-section` / `upsert-section` 优先块级编辑，必要时自动回退到整文档更新
- `append` 会保留 frontmatter 和顶级标题
- 所有写操作都做严格回读校验
- 支持通过 UTF-8 文件输入长 Markdown
- 不依赖第三方 Python 包

## 项目结构

```text
siyuan-cli-skill/
├─ assets/
│  └─ demo-config.svg
├─ CHANGELOG.md
├─ LICENSE
├─ README.md
├─ README.zh-CN.md
├─ SKILL.md
├─ references/
│  └─ api-contract.md
├─ scripts/
│  ├─ siyuan_cli.py
│  ├─ siyuan_client.py
│  ├─ siyuan_config.py
│  └─ siyuan_ops.py
└─ tests/
   ├─ test_siyuan_config.py
   └─ test_siyuan_ops.py
```

## 这个项目解决什么问题

直接在提示词里调用 Siyuan Kernel API 很脆弱：

- 请求体容易写错
- 长 Markdown 内联很啰嗦
- 很多人写完不做回读校验
- 跨平台编码和 shell 差异很容易出问题

这个包装器把下面这些事统一收口了：

- Token 鉴权
- 内容规范化
- 作用域校验
- 块级和文档级写入流程
- 写后回读校验
- 稳定 JSON 输出契约

## 安装方式

### 方案 A：当成独立 CLI 使用

要求：

- Python 3.9+
- 一个可访问的思源实例
- 有效的 Siyuan API Token

```bash
git clone https://github.com/betterLitao/siyuan-cli-skill.git
cd siyuan-cli-skill
```

不需要 `pip install`。这个 CLI 只依赖 Python 标准库。

先设置必需环境变量。

#### macOS / Linux

```bash
export SIYUAN_BASE_URL="http://your-siyuan-host:6806"
export SIYUAN_TOKEN="your-siyuan-token"
```

#### PowerShell

```powershell
$env:SIYUAN_BASE_URL = "http://your-siyuan-host:6806"
$env:SIYUAN_TOKEN = "your-siyuan-token"
```

冒烟测试：

```bash
python3 scripts/siyuan_cli.py config
python3 scripts/siyuan_cli.py config --doctor
```

Windows 下把 `python3` 换成 `python`。

### 方案 B：当成多文件 skill 使用

不要只复制 `SKILL.md`。必须整目录复制。

典型目标结构：

```text
<your-skills-root>/siyuan/
├─ SKILL.md
├─ references/
└─ scripts/
```

然后在复制后的 skill 目录里调用：

```bash
python scripts/siyuan_cli.py config
```

## 快速开始

### Windows

```bash
python scripts/siyuan_cli.py config --doctor
python scripts/siyuan_cli.py search --query "API gateway"
python scripts/siyuan_cli.py read --doc-id "20260314140600-8gkfmc2"
python scripts/siyuan_cli.py update --doc-id "20260314140600-8gkfmc2" --input-file "content.md"
python scripts/siyuan_cli.py append --doc-id "20260314140600-8gkfmc2" --input-file "append.md"
python scripts/siyuan_cli.py replace-section --doc-id "20260314140600-8gkfmc2" --heading "Summary" --input-file "section.md"
python scripts/siyuan_cli.py create-doc --purpose reference --path "Guides/API Wrapper" --input-file "content.md"
python scripts/siyuan_cli.py delete-doc --path "Scratch/Test Doc" --notebook "Inbox" --yes
```

### macOS / Linux

```bash
python3 scripts/siyuan_cli.py config --doctor
python3 scripts/siyuan_cli.py search --query "API gateway"
python3 scripts/siyuan_cli.py read --doc-id "20260314140600-8gkfmc2"
python3 scripts/siyuan_cli.py update --doc-id "20260314140600-8gkfmc2" --input-file "content.md"
python3 scripts/siyuan_cli.py append --doc-id "20260314140600-8gkfmc2" --input-file "append.md"
python3 scripts/siyuan_cli.py replace-section --doc-id "20260314140600-8gkfmc2" --heading "Summary" --input-file "section.md"
python3 scripts/siyuan_cli.py create-doc --purpose reference --path "Guides/API Wrapper" --input-file "content.md"
python3 scripts/siyuan_cli.py delete-doc --path "Scratch/Test Doc" --notebook "Inbox" --yes
```

## 配置模型

必需配置：

- `SIYUAN_BASE_URL` 或 `SIYUAN_URL` 或 `SIYUAN_REMOTE_URL`
- `SIYUAN_TOKEN`

推荐可选配置：

- `SIYUAN_TIMEOUT`
- `SIYUAN_ALLOWED_NOTEBOOKS`
- `SIYUAN_DEFAULT_NOTEBOOK`
- `SIYUAN_PURPOSE_NOTEBOOKS`
- `SIYUAN_CONFIG_FILE`

已废弃但保留兼容：

- `SIYUAN_LEARN_NOTEBOOKS`

### 示例：环境变量

#### macOS / Linux

```bash
export SIYUAN_BASE_URL="http://your-siyuan-host:6806"
export SIYUAN_TOKEN="your-siyuan-token"
export SIYUAN_ALLOWED_NOTEBOOKS="Notes,Projects"
export SIYUAN_DEFAULT_NOTEBOOK="Projects"
export SIYUAN_PURPOSE_NOTEBOOKS="learn=Notes,reference=Projects"
```

#### PowerShell

```powershell
$env:SIYUAN_BASE_URL = "http://your-siyuan-host:6806"
$env:SIYUAN_TOKEN = "your-siyuan-token"
$env:SIYUAN_ALLOWED_NOTEBOOKS = "Notes,Projects"
$env:SIYUAN_DEFAULT_NOTEBOOK = "Projects"
$env:SIYUAN_PURPOSE_NOTEBOOKS = "learn=Notes,reference=Projects"
```

### 示例：配置文件

默认查找路径：

- Windows：`~/.siyuan-cli-skill.json`
- macOS / Linux：`~/.config/siyuan-cli-skill/config.json`

也可以通过 `SIYUAN_CONFIG_FILE` 指定自定义路径。

示例：

```json
{
  "base_url": "http://your-siyuan-host:6806",
  "token": "your-siyuan-token",
  "timeout": 30,
  "allowed_notebooks": ["Notes", "Projects"],
  "default_notebook": "Projects",
  "purpose_notebooks": {
    "learn": "Notes",
    "reference": "Projects"
  }
}
```

环境变量会覆盖配置文件里的同名值。

## 作用域和默认 notebook 行为

notebook 作用域是配置驱动的，不是代码写死的。

- 如果设置了 `SIYUAN_ALLOWED_NOTEBOOKS`，操作会被限制在这个白名单里。
- 如果 `SIYUAN_ALLOWED_NOTEBOOKS` 为空，CLI 不会强制限制 notebook 白名单。
- `create-doc` 解析目标 notebook 的顺序是：
  1. 显式 `--notebook`
  2. `purpose_notebooks[--purpose]`
  3. `default_notebook`
  4. `allowed_notebooks` 的第一个值
  5. 以上都没有时直接失败并要求传 `--notebook`

兼容规则：

- 如果设置了 `SIYUAN_LEARN_NOTEBOOKS`，且没有配置 `purpose_notebooks.learn`，那么旧的第一个 learn notebook 会被当成 `purpose=learn`

## 诊断能力

当你感觉配置“莫名其妙丢了”时，直接用 doctor 模式：

```bash
python3 scripts/siyuan_cli.py config --doctor
```

doctor 会显示：

- 当前生效的 scope 和默认 notebook
- purpose 映射
- 配置文件路径和解析错误
- 每个值到底来自哪里
- 缺失的必需配置
- 当 Windows 全局环境变量存在但当前进程没继承时的诊断提示
- Windows 下的 process、user、machine 三层环境变量

这能直接看出一个值到底只存在于全局环境变量、只存在于当前 shell，还是根本没加载进来。

重要：

- 在 Windows 下，如果某个值只出现在 `user` 或 `machine` 层，那它还不算当前进程已生效，必须让新的 shell 或宿主应用重新继承。
- 跨设备同步 skill 文件，并不会把运行时配置自动注入到当前进程。每台机器仍然要有自己的环境变量或 config file 路径。

## 路径处理说明

- Windows Git Bash 下，不要让思源路径以 `/` 开头。
- 优先写成 `Guides/API Wrapper`，不要写 `/Guides/API Wrapper`。
- 路径规范化会自动把 `\` 转成 `/`、去掉 `.sy`、清理空格，并统一成思源 hpath。

## 鉴权模型

这个项目使用 Token 鉴权。

- 请求认证依赖 `SIYUAN_TOKEN`
- `accessAuthCode` 更偏向思源服务暴露或启动配置
- 它不是这个 CLI 日常请求使用的认证头

## 写入策略

所有写入流程都遵循同一套步骤：

1. 从 `--text` 或 `--input-file` 读取 Markdown
2. 把换行统一成 `\n`
3. 清理非法控制字符
4. 调用对应的 Siyuan API
5. 回读文档
6. 校验结果
7. 输出结构化 JSON

额外保证：

- `append` 不会只回写 editable body，它会保留 frontmatter 和顶级标题
- `replace-section` 优先块级编辑，但当块匹配不可靠时会自动回退到整文档更新
- 回读校验必须是整文档精确匹配，或 editable body 精确匹配，禁止子串误判成功

## 发布说明

看 [`CHANGELOG.md`](CHANGELOG.md)。

## 维护建议

- `SKILL.md` 只负责调用策略
- `references/api-contract.md` 只负责 CLI 契约细节
- `scripts/` 是稳定执行层
- 改写入逻辑前先补隐藏回归测试
