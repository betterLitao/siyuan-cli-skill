---
name: siyuan
description: 通过稳定的 Python CLI 包装器操作文档（读取、搜索、更新、追加、创建），避免直接手搓思源 Kernel API 请求体。
---

# 思源笔记文档管理

这是一个 **多文件 skill**。

- 源头目录：`E:/cc-switch/skills/siyuan`
- 需要整目录同步，不要只复制 `SKILL.md`
- 主路径是 `scripts/siyuan_cli.py`
- `Invoke-RestMethod` / `ssh + curl` 只保留为应急 fallback，不再作为主调用方式

## 主调用路径

优先使用 CLI：

### Windows

```bash
python scripts/siyuan_cli.py <command> [...args]
```

### macOS

```bash
python3 scripts/siyuan_cli.py <command> [...args]
```

## 可用命令

- `read`
- `search`
- `update`
- `append`
- `replace-section`
- `upsert-section`
- `create-doc`
- `delete-doc`
- `config`

统一输出 JSON，字段至少包含：

- `ok`
- `action`
- `message`
- `data`
- `error`

详细契约见：`references/api-contract.md`

## 硬规则

1. **优先使用 CLI，不直接拼 Kernel API body。**
2. **长文本写入优先 `--input-file`。**
3. **目标不明确时先 `search`，多个候选时先问用户。**
4. **写入后必须回读校验。**
5. **默认只处理 `服务器运维` / `learn`。**
6. **不要默认跨目录扫描或写入其它 notebook。**
7. **优先改 section，不要动不动整篇重写。**
8. **文档 ID / 路径解析优先走官方 `filetree` 接口，SQL 只保留给检索等必要场景。**
9. **API 鉴权只认 `Token`；不要把 `accessAuthCode` / `SIYUAN_AUTH_CODE` 当成请求头凭证。**

## 推荐工作流

### 读取已知文档

```bash
python scripts/siyuan_cli.py read --doc-id "20260314140600-8gkfmc2"
```

或：

```bash
python scripts/siyuan_cli.py read --path "运维指南" --notebook "服务器运维"
```

在 Windows Git Bash 里，不要把思源文档路径写成 `"/运维指南"` 这种以 `/` 开头的参数；Git Bash 可能会自动改写成磁盘路径。优先写成 `"运维指南"` 或 `"运维指南/SSH 免密登录"`。

路径归一化现在会自动去掉分隔符两侧多余空格：

- `"工具 / 工作流/文档"` 会被规范成 `"/工具/工作流/文档"`
- 所以保留你平时爱写的这种路径风格也没问题

`read` 返回里现在有两套内容视图：

- `content` / `raw_content`：思源 `exportMdContent` 原样导出的 Markdown，可能带 frontmatter 和顶层标题
- `editable_content`：已经剥掉 frontmatter 和顶层标题的正文视图，更适合后续修改

### 搜索候选文档

```bash
python scripts/siyuan_cli.py search --query "OpenClaw"
```

如果返回多个候选，不要擅自改，先基于 `hpath` / `content` 问用户要哪一个。

### 整体更新文档

长文本优先：

```bash
python scripts/siyuan_cli.py update --doc-id "20260314140600-8gkfmc2" --input-file "content.md"
```

短文本才考虑：

```bash
python scripts/siyuan_cli.py update --doc-id "20260314140600-8gkfmc2" --text "# 标题"
```

### 追加到文档尾部

```bash
python scripts/siyuan_cli.py append --doc-id "20260314140600-8gkfmc2" --input-file "append.md"
```

### 只替换某个标题下的 section

优先用这个，不要整篇覆盖：

```bash
python scripts/siyuan_cli.py replace-section --doc-id "20260314140600-8gkfmc2" --heading "注意事项 / 坑点" --input-file "section.md"
```

如果标题不存在就自动创建：

```bash
python scripts/siyuan_cli.py upsert-section --doc-id "20260314140600-8gkfmc2" --heading "结论" --input-file "section.md"
```

也可以显式指定标题级别：

```bash
python scripts/siyuan_cli.py upsert-section --doc-id "20260314140600-8gkfmc2" --heading "结论" --level 2 --input-file "section.md"
```

现在这两个命令优先走块级编辑：

- 保留目标标题块本身
- 只删除该标题下旧的子块
- 再插入新的 Markdown 子块
- 缺少目标标题时，`upsert-section` 会在文档尾部按块创建新 section

### 创建新文档

默认用途：

```bash
python scripts/siyuan_cli.py create-doc --path "运维指南/新文档" --input-file "content.md"
```

保存到学习目录：

```bash
python scripts/siyuan_cli.py create-doc --purpose learn --path "工具 / 工作流/思源稳定写入包装器" --input-file "content.md"
```

如果目标路径已存在，显式指定策略：

```bash
python scripts/siyuan_cli.py create-doc --purpose learn --path "工具 / 工作流/思源稳定写入包装器" --input-file "content.md" --if-exists skip
python scripts/siyuan_cli.py create-doc --purpose learn --path "工具 / 工作流/思源稳定写入包装器" --input-file "content.md" --if-exists replace
```

`--if-exists` 可选值：

- `error`：默认值，路径已存在就直接报错
- `skip`：不新建，直接返回现有文档内容
- `replace`：不新建，直接把现有文档整体替换成新内容

### 删除文档

必须显式确认：

```bash
python scripts/siyuan_cli.py delete-doc --doc-id "20260314140600-8gkfmc2" --yes
python scripts/siyuan_cli.py delete-doc --path "工具 / 工作流/临时测试文档" --notebook "learn" --yes
```

删除逻辑：

- 先解析目标文档
- 先回读保留删除前内容
- 再调用官方 `removeDoc`
- 最后做删除后校验，确认文档 ID / hpath 不再存在

## 默认范围与收敛规则

默认只处理以下目录，除非用户明确指定并且配置层已放开：

- `服务器运维` 笔记本：默认允许读取、查询、更新、创建文档
- `learn` / “学习”目录：仅用于整理教程或总结类文档（按需创建/更新）

不做的事（除非用户显式说明）：

- 不扫描或批量读取 `我的文档` / `workspace` 等其它目录
- 不跨目录做全文检索
- 不自动把内容写入非 `服务器运维` / `learn` 目录

如果用户未指定目录又需要读取内容，优先只读 `服务器运维`；如与需求无关，再询问是否允许读取其它目录。

## 搜索语义

`search` 不再只是“看文档标题有没有这个词”。

现在会在允许范围内搜索：

- 文档标题 / 路径
- 文档正文里的普通块内容

然后返回命中的根文档列表。

注意：

- 当前正文检索底层仍然依赖 `query/sql`
- 如果思源运行在发布模式且未开放对应读写权限，`search` 可能不可用
- 这种场景下优先改用 `read --doc-id` 或 `read --path + --notebook` 做精确读取

## 特定话术约定

当用户说以下类似话术时，默认理解为：把当前对话中的关键信息整理后，保存到思源的 `learn` / “学习”目录，而不是只在当前对话里口头总结。

- “保存到学习目录”
- “保存到 learn 目录”
- “保存到学习文档”
- “记到学习目录”
- “沉淀到 learn”
- 其他明显表示“把经验/结论归档到学习文档”的近义表达

默认动作：

1. 先总结当前信息，去掉闲聊、重复和过程噪音。
2. 再判断分类，落到 `learn` / “学习”目录下对应菜单。
3. 如果是补充已有主题，优先更新已有文档；否则创建新文档。
4. 如果同时存在多个同名/近似目录，再基于 `hpath` 选择最像 “learn/学习” 的那一个。

## learn 目录分类规则

当用户只说“保存到学习目录”，但没指定分类时，按内容自动归类。优先使用下面这些菜单：

- `AI / 模型 / Prompt`
  - 模型能力、提示词、Agent、工具调用、OpenAI / Anthropic / Claude / Codex / OpenClaw 相关经验

- `开发 / 前端`
  - UI、Vue、React、CSS、组件设计、交互实现、前端工程经验

- `开发 / 后端`
  - API、服务端、数据库、中间件、部署接口、鉴权、架构设计

- `运维 / 服务器`
  - Linux、systemd、Nginx、Docker、VPS、端口、进程、日志、网络

- `故障排查 / 复盘`
  - 某次问题的现象、根因、修复、规避方案、注意事项

- `工具 / 工作流`
  - CLI、脚本、自动化、插件、Skill、MCP、效率工具、协作流程

分类判定规则：

- 涉及模型能力、工具暴露、搜索、图片识别、Prompt、Agent，优先归到 `AI / 模型 / Prompt`
- 涉及服务器、systemd、网关、部署、重启、安全脚本，优先归到 `运维 / 服务器`
- 涉及某次事故、根因分析、修复过程，优先归到 `故障排查 / 复盘`
- 涉及脚本、Skill、命令流、自动化链路，优先归到 `工具 / 工作流`
- 如果内容明显跨多个分类，优先选“最能代表后续检索入口”的那一个，不要一份内容拆很多份

## 保存到 learn 时的文档写法

保存到学习目录时，默认用“结论优先”的整理方式，不要把整段聊天原样塞进去。

推荐结构：

```md
# 标题

## 背景

## 结论

## 关键细节

## 注意事项 / 坑点
```

写法要求：

- 标题要能直接反映主题，不要用“随手记录”“一点笔记”这种废标题
- 内容优先保留结论、原因、限制、操作方法
- 删掉无意义对话语气、重复解释、试错噪音
- 如果是复盘类内容，要明确写“现象 / 根因 / 修复 / 规避”
- 如果是知识总结类内容，要明确写“是什么 / 为什么 / 怎么用 / 限制”

## 应急 fallback

只有在 CLI 路径不可用时，才考虑直接调用原始 API：

### Windows / PowerShell

```powershell
$headers = @{ Authorization = 'Token <your-siyuan-token>' }
$body = @{ id = '<块ID>' } | ConvertTo-Json -Compress
Invoke-RestMethod -Method Post `
  -Uri 'http://<your-siyuan-host>:6806/api/export/exportMdContent' `
  -Headers $headers `
  -ContentType 'application/json' `
  -Body $body
```

### macOS / Linux / 通用 shell

```bash
ssh <your-user>@<your-siyuan-host> "curl -s -X POST http://127.0.0.1:6806/api/<endpoint> -H 'Authorization: Token <your-siyuan-token>' -H 'Content-Type: application/json' -d '<json>'"
```

但这条路径仅用于故障应急，不应作为默认方案。
