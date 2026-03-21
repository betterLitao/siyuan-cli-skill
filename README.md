# siyuan

这是一个 **多文件 skill**，源头位于 `E:/cc-switch/skills/siyuan`。

## 重要说明

- 这个 skill 已不再是只靠 `SKILL.md` 的单文件 skill。
- 需要和 `scripts/`、`references/` 一起按**整个目录**同步。
- 如果只复制 `SKILL.md`，CLI 包装器会缺失，长文本写入仍会回到不稳定路径。

## 目录结构

```text
siyuan/
├─ SKILL.md
├─ README.md
├─ references/
│  └─ api-contract.md
└─ scripts/
   ├─ siyuan_cli.py
   ├─ siyuan_client.py
   ├─ siyuan_config.py
   └─ siyuan_ops.py
```

## 设计目标

把思源 Kernel API 的 JSON 拼装、UTF-8 编码、控制字符清洗、写后回读校验，统一沉到 Python CLI 包装器里。

这样模型只需要：

1. 生成 Markdown 内容
2. 选择 `read/search/update/append/replace-section/upsert-section/create-doc/delete-doc` 命令
3. 对长文本优先用 `--input-file`

## CLI 入口

### Windows

```bash
python scripts/siyuan_cli.py config
python scripts/siyuan_cli.py search --query "OpenClaw"
python scripts/siyuan_cli.py read --doc-id "20260314140600-8gkfmc2"
python scripts/siyuan_cli.py update --doc-id "20260314140600-8gkfmc2" --input-file "content.md"
python scripts/siyuan_cli.py append --doc-id "20260314140600-8gkfmc2" --input-file "append.md"
python scripts/siyuan_cli.py replace-section --doc-id "20260314140600-8gkfmc2" --heading "结论" --input-file "section.md"
python scripts/siyuan_cli.py upsert-section --doc-id "20260314140600-8gkfmc2" --heading "注意事项 / 坑点" --input-file "section.md"
python scripts/siyuan_cli.py create-doc --purpose learn --path "工具 / 工作流/思源稳定写入包装器" --input-file "content.md"
python scripts/siyuan_cli.py delete-doc --path "工具 / 工作流/临时测试文档" --notebook "learn" --yes
```

在 Windows Git Bash 里，思源文档路径不要以 `/` 开头，避免被自动改写成 Windows 磁盘路径。

路径里的分隔符两侧空格会自动清理，所以 `工具 / 工作流/文档` 这种写法会自动规范成 `/工具/工作流/文档`。

### macOS

```bash
python3 scripts/siyuan_cli.py config
python3 scripts/siyuan_cli.py search --query "OpenClaw"
python3 scripts/siyuan_cli.py read --doc-id "20260314140600-8gkfmc2"
python3 scripts/siyuan_cli.py update --doc-id "20260314140600-8gkfmc2" --input-file "content.md"
python3 scripts/siyuan_cli.py append --doc-id "20260314140600-8gkfmc2" --input-file "append.md"
python3 scripts/siyuan_cli.py replace-section --doc-id "20260314140600-8gkfmc2" --heading "结论" --input-file "section.md"
python3 scripts/siyuan_cli.py upsert-section --doc-id "20260314140600-8gkfmc2" --heading "注意事项 / 坑点" --input-file "section.md"
python3 scripts/siyuan_cli.py create-doc --purpose learn --path "/工具 / 工作流/思源稳定写入包装器" --input-file "content.md"
python3 scripts/siyuan_cli.py delete-doc --path "工具 / 工作流/临时测试文档" --notebook "learn" --yes
```

`read` 现在会同时返回：

- `content` / `raw_content`：思源导出的原始 Markdown
- `editable_content`：剥掉 frontmatter 和顶层标题后的正文，更适合继续修改

## 搜索与写入增强

- 文档 `ID / hpath` 解析优先走官方 `filetree` API，不再默认依赖 SQL 查文档元信息
- `search` 现在会命中文档标题、路径和正文块内容，不再只是偏标题搜索
- `search` 的正文检索仍依赖 `query/sql`；如果思源处于发布模式且权限未开放，这个能力可能不可用
- `replace-section` / `upsert-section` 现在优先走块级编辑：保留标题块，只替换该 section 子块
- `upsert-section` 在标题不存在时，会在文档尾部按块创建新 section
- `create-doc` 新增 `--if-exists error|skip|replace`，路径冲突行为变成显式策略
- `delete-doc` 新增显式删除入口，必须带 `--yes` 才会执行
- 写入校验现在会同时比较原始导出和可编辑正文视图，减少误报

## 环境变量

脚本现在不再在源码里内置默认 `base_url/token`。

必须通过环境变量提供：

- `SIYUAN_BASE_URL`
- `SIYUAN_TOKEN`

兼容别名：

- `SIYUAN_URL`
- `SIYUAN_REMOTE_URL`

可选项：

- `SIYUAN_TIMEOUT`
- `SIYUAN_ALLOWED_NOTEBOOKS`
- `SIYUAN_LEARN_NOTEBOOKS`

说明：

- API 请求鉴权核心是 `SIYUAN_TOKEN`
- `accessAuthCode` 更偏向思源服务启动/网络暴露配置，不是这个 CLI 每次请求要传的认证头
- 所以 `SIYUAN_AUTH_CODE` 已从这个 skill 的运行配置里移除

macOS / zsh 示例：

```bash
export SIYUAN_BASE_URL="http://your-siyuan-host:6806"
export SIYUAN_TOKEN="your-siyuan-token"
```

Windows / PowerShell 示例：

```powershell
$env:SIYUAN_BASE_URL = "http://your-siyuan-host:6806"
$env:SIYUAN_TOKEN = "your-siyuan-token"
```

## 范围约束

默认只允许处理：

- `服务器运维`
- `learn`

不默认：

- 扫描 `workspace` / `我的文档`
- 跨目录全文检索
- 写入其它 notebook

如确需处理其它 notebook，应先调整配置层，而不是在提示词里临时放开。

## 写入策略

所有写入类命令都遵循统一流程：

1. 读取输入 Markdown（优先 `--input-file`）
2. 统一换行为 `\n`
3. 清理非法控制字符
4. 调用思源写入接口
5. 回读 `exportMdContent`
6. 输出结构化 JSON

## 维护建议

- `SKILL.md` 负责调用策略，不负责协议细节。
- `references/api-contract.md` 负责记录 CLI 输入输出契约。
- 如后续要同步到另一台 mac 主机，必须整目录同步，不要只同步 `SKILL.md`。
- 本次改造仅修改源头 skill；是否同步到 app 派生副本，由用户后续自行决定。
