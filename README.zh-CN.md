# siyuan-cli-skill

[English](README.md)

![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-6f42c1.svg)

一个可复用的多文件 skill，用来实现 **稳定的思源文档读写**。

它把 Siyuan Kernel API 包装成一个 Python CLI，这样助手或自动化脚本就不用再手搓请求体来做常见文档操作。

## 演示

![Siyuan CLI config demo](assets/demo-config.svg)

## 特性

- 所有命令统一输出结构化 JSON
- 支持 read / search / update / append / create / delete 文档操作
- `replace-section` / `upsert-section` 优先走块级编辑
- `create-doc --if-exists` 冲突策略显式可控
- 所有写操作都带回读校验
- 支持通过 UTF-8 文件输入长 Markdown
- 不依赖第三方 Python 包
- 兼容 Windows、macOS、Linux

## 项目结构

```text
siyuan-cli-skill/
├─ assets/
│  └─ demo-config.svg
├─ CHANGELOG.md
├─ LICENSE
├─ SKILL.md
├─ README.md
├─ README.zh-CN.md
├─ references/
│  └─ api-contract.md
└─ scripts/
   ├─ siyuan_cli.py
   ├─ siyuan_client.py
   ├─ siyuan_config.py
   └─ siyuan_ops.py
```

## 这个项目解决什么问题

直接在提示词里调用 Siyuan Kernel API 很脆弱：

- 请求体很容易拼错
- 长 Markdown 内联很啰嗦
- 很多人写完不做回读校验
- 跨平台编码问题很容易炸

这个包装器把下面这些事统一收口了：

- 基于环境变量的鉴权
- 内容规范化
- 文档级 / 块级写入流程
- 写后回读校验
- 稳定的 JSON 输出契约

## 安装方式

### 方案 A：当成独立 CLI 使用

要求：

- Python 3.9+
- 一个可访问的思源实例
- 有效的 Siyuan API Token

克隆仓库：

```bash
git clone https://github.com/betterLitao/siyuan-cli-skill.git
cd siyuan-cli-skill
```

不需要 `pip install`。这个 CLI 只依赖 Python 标准库。

设置必需环境变量。

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

先跑一个冒烟测试：

```bash
python3 scripts/siyuan_cli.py config
```

Windows 下用：

```bash
python scripts/siyuan_cli.py config
```

### 方案 B：当成多文件 skill 使用

**不要只复制 `SKILL.md`。** 必须整目录复制。

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
python scripts/siyuan_cli.py config
python scripts/siyuan_cli.py search --query "API gateway"
python scripts/siyuan_cli.py read --doc-id "20260314140600-8gkfmc2"
python scripts/siyuan_cli.py update --doc-id "20260314140600-8gkfmc2" --input-file "content.md"
python scripts/siyuan_cli.py replace-section --doc-id "20260314140600-8gkfmc2" --heading "Summary" --input-file "section.md"
python scripts/siyuan_cli.py create-doc --notebook "Projects" --path "Guides/API Wrapper" --input-file "content.md"
python scripts/siyuan_cli.py delete-doc --path "Scratch/Test Doc" --notebook "Inbox" --yes
```

### macOS / Linux

```bash
python3 scripts/siyuan_cli.py config
python3 scripts/siyuan_cli.py search --query "API gateway"
python3 scripts/siyuan_cli.py read --doc-id "20260314140600-8gkfmc2"
python3 scripts/siyuan_cli.py update --doc-id "20260314140600-8gkfmc2" --input-file "content.md"
python3 scripts/siyuan_cli.py replace-section --doc-id "20260314140600-8gkfmc2" --heading "Summary" --input-file "section.md"
python3 scripts/siyuan_cli.py create-doc --notebook "Projects" --path "Guides/API Wrapper" --input-file "content.md"
python3 scripts/siyuan_cli.py delete-doc --path "Scratch/Test Doc" --notebook "Inbox" --yes
```

## 路径处理说明

- 在 Windows Git Bash 里，**不要**让思源路径以 `/` 开头。
- 优先写成 `Guides/API Wrapper`，不要写 `/Guides/API Wrapper`。
- 路径规范化会自动做这些事：
  - 把 `\\` 转成 `/`
  - 去掉 `.sy`
  - 清理分隔符两边多余空格
  - 内部统一成思源 hpath 格式

## 环境变量

必需：

- `SIYUAN_BASE_URL` 或 `SIYUAN_URL` 或 `SIYUAN_REMOTE_URL`
- `SIYUAN_TOKEN`

可选：

- `SIYUAN_TIMEOUT`
- `SIYUAN_ALLOWED_NOTEBOOKS`
- `SIYUAN_LEARN_NOTEBOOKS`

### 示例：macOS / Linux

```bash
export SIYUAN_BASE_URL="http://your-siyuan-host:6806"
export SIYUAN_TOKEN="your-siyuan-token"
export SIYUAN_ALLOWED_NOTEBOOKS="Notes,Projects"
export SIYUAN_LEARN_NOTEBOOKS="Notes"
```

### 示例：PowerShell

```powershell
$env:SIYUAN_BASE_URL = "http://your-siyuan-host:6806"
$env:SIYUAN_TOKEN = "your-siyuan-token"
$env:SIYUAN_ALLOWED_NOTEBOOKS = "Notes,Projects"
$env:SIYUAN_LEARN_NOTEBOOKS = "Notes"
```

## 作用域行为

notebook 作用域是**配置驱动**的，不是代码写死的。

- 如果配置了 `SIYUAN_ALLOWED_NOTEBOOKS`，操作会被限制在这个白名单里。
- 如果 `SIYUAN_ALLOWED_NOTEBOOKS` 为空，CLI 不会强制限制 notebook 白名单。
- `create-doc` 只有在能解析出默认 notebook 时，才可以省略 `--notebook`：
  - `--purpose learn` 时优先取 `SIYUAN_LEARN_NOTEBOOKS`
  - 否则取 `SIYUAN_ALLOWED_NOTEBOOKS` 的第一个值
- 如果默认 notebook 无法解析，`create-doc` 会直接报错并要求显式传 `--notebook`。

## 鉴权模型

这个项目使用 **Token 鉴权**。

重点：

- 请求认证依赖的是 `SIYUAN_TOKEN`
- `accessAuthCode` 更偏向思源服务暴露 / 启动配置
- 它**不是**这个 CLI 日常请求使用的认证头

## 发布说明

看 [`CHANGELOG.md`](CHANGELOG.md)。

当前公开基线版本：**v1.0.0**。

## 写入策略

所有写入流程都遵循同一套步骤：

1. 读取 Markdown（长内容优先 `--input-file`）
2. 把换行统一成 `\n`
3. 清理非法控制字符
4. 调用对应的 Siyuan API
5. 回读文档
6. 校验结果
7. 输出结构化 JSON

## 维护建议

- `SKILL.md` 只负责调用策略，不负责协议细节
- `references/api-contract.md` 负责 CLI 契约细节
- `scripts/` 是稳定执行层
- 如果你要分发这个 skill，复制整目录，不要只复制 `SKILL.md`
