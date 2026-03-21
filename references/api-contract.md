# Siyuan CLI API Contract

`scripts/siyuan_cli.py` 的目标是给 skill 提供稳定、结构化、跨平台一致的读写接口。

## 输出格式

所有命令都输出 JSON，对外字段保持统一：

```json
{
  "ok": true,
  "action": "read",
  "message": "Read document successfully.",
  "data": {},
  "error": null
}
```

失败时：

```json
{
  "ok": false,
  "action": "update",
  "message": "Notebook 'workspace' is outside the default allowed scope.",
  "data": null,
  "error": {
    "type": "SiyuanError",
    "action": "scope-check",
    "message": "Notebook 'workspace' is outside the default allowed scope.",
    "details": {
      "requested": "workspace",
      "allowed": ["服务器运维", "learn"]
    }
  }
}
```

## 命令约定

### `config`

输出当前生效的连接配置与 notebook 范围。

### `read`

输入：

- `--doc-id <id>`，或
- `--path <path> --notebook <name>`

说明：Windows Git Bash 下，`--path` 建议传 `运维指南/SSH 免密登录` 这种不以 `/` 开头的思源人类路径，避免被自动改写成磁盘路径。

路径归一化会自动：

- 把 `\` 转成 `/`
- 去掉 `.sy`
- 去掉分隔符两侧多余空格
- 统一补成以 `/` 开头的思源 hpath

输出 `data`：

- `id`
- `hPath`
- `content`
- `raw_content`
- `editable_content`
- `title`
- `resolved_from`
- `meta`

说明：

- `content` 与 `raw_content` 当前等价，都是思源导出的原始 Markdown
- `editable_content` 是去掉 frontmatter 和顶层标题后的正文视图，优先给后续更新命令使用

### `search`

输入：

- `--query <keyword>`
- `--notebook <name>` 可选
- `--limit <n>` 可选

输出 `data`：

- `query`
- `notebook`
- `count`
- `items`

`items` 内部至少包含：

- `id`
- `box`
- `path`
- `hpath`
- `content`
- `root_id`

说明：

- `search` 会在允许范围内搜索文档标题、路径以及正文块内容
- 返回仍然收敛到根文档列表，不直接返回零散块
- 当前正文检索依赖 `query/sql`；如果思源运行在发布模式且权限未开放，检索可能失败

### `update`

输入：

- `--doc-id <id>`，或 `--path + --notebook`
- `--text <markdown>` 或 `--input-file <file>`

行为：

1. 读取旧内容
2. 整体替换文档 Markdown
3. 回读校验

输出 `data`：

- `id`
- `before`
- `after`
- `verified`
- `mismatch_reason`
- `meta`

### `append`

输入：

- `--doc-id <id>`，或 `--path + --notebook`
- `--text <markdown>` 或 `--input-file <file>`

行为：

1. 读取旧内容
2. 以整体重写方式在尾部追加
3. 回读校验

输出 `data`：

- `id`
- `before`
- `after`
- `verified`
- `mismatch_reason`
- `appended_markdown`
- `meta`

### `replace-section`

输入：

- `--doc-id <id>`，或 `--path + --notebook`
- `--heading <text>`，支持 `结论` 或 `## 结论`
- `--level <n>` 可选，只有当 `--heading` 是纯文本时才需要
- `--text <markdown>` 或 `--input-file <file>`

行为：

1. 读取当前文档正文视图
2. 找到指定标题 section
3. 保留标题块本身，只替换该标题下的子块
4. 回读校验

输出 `data`：

- `id`
- `before`
- `after`
- `verified`
- `mismatch_reason`
- `mode`
- `section`
- `meta`

### `upsert-section`

输入：

- 同 `replace-section`

行为：

1. 读取当前文档正文视图
2. 如果标题存在则替换
3. 如果标题不存在则在文档尾部创建新 section
4. 回读校验

输出 `data`：

- 同 `replace-section`

### `create-doc`

输入：

- `--path <path>`
- `--text <markdown>` 或 `--input-file <file>`
- `--notebook <name>` 可选
- `--if-exists error|skip|replace` 可选
- `--purpose learn|default` 可选，用于选择默认 notebook

行为：

1. 先检查目标路径是否已存在
2. 根据 `--if-exists` 选择报错、跳过或替换
3. 创建或复用目标文档
4. 立即回读

输出 `data`：

- `id`
- `notebook`
- `notebook_id`
- `path`
- `content`
- `hPath`
- `verified`
- `mismatch_reason`
- `created`
- `skipped`
- `if_exists`

### `delete-doc`

输入：

- `--doc-id <id>`，或 `--path + --notebook`
- `--yes` 必填，用于显式确认删除

行为：

1. 解析目标文档
2. 回读保留删除前内容
3. 调用官方 `removeDoc`
4. 再做删除后校验，确认文档 ID / hpath 不再存在

输出 `data`：

- `id`
- `notebook_id`
- `path`
- `hpath`
- `before`
- `verified`
- `deleted`
- `exists_after_id`
- `remaining_doc_ids`
- `meta`

## 作用域约束

CLI 默认只允许：

- `服务器运维`
- `learn`

如果请求落到其它 notebook，CLI 直接失败，除非先调整配置层。

## 内容输入约束

- 长 Markdown 优先 `--input-file`
- 文件必须按 UTF-8 读取
- CLI 内部统一做：
  - `\r\n` / `\r` -> `\n`
  - 清理非法控制字符
  - `json.dumps(..., ensure_ascii=False)`

## 回读校验

写入类命令必须回读 `exportMdContent`。

当前判定规则：

1. `expected.strip() == actual.strip()` -> 成功
2. 或 `expected.strip() == editable_actual.strip()` -> 成功
3. 或 `expected.strip()` 是 `actual.strip()` / `editable_actual.strip()` 的子串 -> 成功
4. 否则 `verified=false`，并返回 `mismatch_reason`
