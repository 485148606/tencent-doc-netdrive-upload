---
name: 腾讯文档 / 腾讯网盘 上传（本地直连版）
description: >-
  【腾讯文档 / 腾讯网盘 上传（本地直连版）】>- 【腾讯文档 / 腾讯网盘 上传（本地直连版）】把本地大文件（长 Markdown / 剧本 / 报告）发到腾讯生态让用户"能点开看"——① 传腾讯网盘（tdrive，可映射到用户桌面目录）；② 建成腾讯在线文档并拿到可点链接。两者都走本地 Python 直连 HTTP，绕开 MCP 传输体积上限和 shell 转义坑。触发词：放到网盘、加到那个文件夹、发我一份能点开的、生成在线文档、文档太长发不出去、网盘上传、tdrive 上传。
agent_created: true
---

# 腾讯文档 / 腾讯网盘 上传（本地直连版）

## 什么时候用

- 用户说「文件我打不开 / 在哪呢 / 发到对话里 / 放到那个文件夹里 / 生成个在线文档」。
- 产物是**本地文件**，且**体积大**（几百 KB 以上的 Markdown、剧本、报告）。
- 目标是把内容**送到用户手上**，不是留在本地路径里。

## 大前提：先判断「发」的通道

| 通道 | 适用 | 本 skill 覆盖 |
|---|---|---|
| `present_files` 工具 | 会话里有这个工具时首选 | ✗（工具缺失时看下面） |
| **腾讯在线文档**（docs.qq.com） | 用户要「在对话里点开就看」 | ✔ 方案 A |
| **腾讯网盘**（tdrive） | 用户要「放到我的某个文件夹/桌面目录」 | ✔ 方案 B |
| 复制到桌面 | 兜底，Bash `cp` 可用 | ✔ 方案 C |

> ⚠️ **`present_files` 可能在某些会话轮次不可用（调用报 Tool Not Found）**。一旦不可用，**不要只说「已生成」+ 本地路径**——用户看不到就等于没做。立刻转方案 A/B/C。

---

## 方案 A：本地长 Markdown → 腾讯在线文档

```bash
AUTH=$(python -c "import json,os;print(json.load(open(os.path.expanduser('~/.workbuddy/mcp.json'),encoding='utf-8'))['mcpServers']['tencent-docs-doc']['headers']['Authorization'])")

python -u create_with_markdown.py \
  --mcp-url "https://docs.qq.com/api/v6/doc/mcp" \
  --auth "$AUTH" \
  --markdown-path "D:/path/to/big.md" \
  --title "文档标题"
```

- **端点必须是 `https://docs.qq.com/api/v6/doc/mcp`**（`tencent-docs-doc` 那条）。
  用 `https://docs.qq.com/openapi/mcp` 也可以，但 tool 名前缀规则不同。
- 端点里**不含 `saas.docs.qq.com`** → tool 名用 `create_with_markdown`；含则用 `doc.create_with_markdown`。
- auth 来源：`~/.workbuddy/mcp.json` → `mcpServers['tencent-docs-doc'].headers.Authorization`（值形如 `Bearer xxx`）。
- **走本地 Python 直连 HTTP，不要用 MCP 工具直传 base64**——365 KB 的 md 直传会被传输上限掐死。
- 返回 `{"file_id":"xxx","file_url":"//docs.qq.com/doc/XXXX"}`。

**给用户的链接格式**（系统约定）：
```
https://docs.qq.com/doc/<file_url 后半段>?_fid=<file_id>
```

**验证已写入完整内容**：`mcp__tencent-docs-doc__get_outline`（传 `file_id`），看 outlines 是否到最后一节。

> 前置：腾讯文档 MCP 必须已登录。先 `mcp__tencent-docs__get_user_info` 探一下，返回昵称即为已鉴权。

---

## 方案 B：本地文件 → 腾讯网盘（tdrive）

> ⚠️ **动手前先探测工具是否在册**：`ToolSearch(tool_names:["mcp__netdrive__tdrive.file_upload"])`。
> 若返回 `not available` / `not found in the deferred tools index` → **netdrive MCP 整组没挂上**，
> 方案 B 走不通（拿不到 `confirm_key`）。此时：
> 1. 别反复换个名字试（`netdrive__tdrive.*`、`mcp__netdrive__tdrive.*` 都一样没）；
> 2. 也不要指望本机有 tdrive 配置可绕（`~/.workbuddy/` 下没有 netdrive 映射）；
> 3. **直接转方案 A（腾讯在线文档）或方案 C（桌面）**，并在回复里讲清楚"项目盘那份没同步"，
>    给出下次工具恢复后再传的待办。

**必须三步，少一步文件就不出现。**

**第 1 步** `mcp__netdrive__tdrive.file_upload`
```json
{"dir_id": "<目标目录ID>", "file_name": "xxx.md", "file_size": 365180, "conflict_strategy": "rename"}
```
返回 `domain / path / headers / confirm_key / task_id`。

**第 2 步** PUT 上传本地文件（**用 Python，别用 shell curl**）
- URL = `https://` + `domain` + `path`
- `headers` 里每一对**原样**带上
- ⚠️ `Authorization` 里塞了几十个 `&`，**shell 里必被转义搞坏** → 用 `nd_put.py`；把第 1 步的响应 JSON 落盘再喂给脚本，**用完立刻删**（含 `x-cos-security-token`）
- 见到 `HTTP 200 bytes <大小>` 即成功

**第 3 步** `mcp__netdrive__tdrive.file_upload_complete`
```json
{"confirm_key":"...","task_id":"...","dir_id":"...","file_name":"xxx.md","file_size":365180}
```
返回 `file_id`。

**验证**：`mcp__netdrive__tdrive.dir_list`（传 `dir_id`）看 `total_num` 和条目列表。

**找目标目录**：用户给的是 `netdrive://` 引用或文件夹名。
- 引用块里有 `<file id="XXXX" item_type="folder" />` → 那个 id 就是 `dir_id`。
- 只有名字 → 用 `tdrive.search_file` 找。

**同名冲突**：`conflict_strategy` = `ask`（默认，报错）/ `rename`（自动改名）/ `overwrite`（覆盖）。
不确定就先 `dir_list` 看里面有什么，**别盲目 overwrite 用户已有的文件**。

---

## 方案 C：兜底——复制到桌面

```bash
cp "D:/workbuddy/.../文件.md" "/c/Users/Administrator/Desktop/《名字》.md"
```
- **可用**。反过来，PowerShell 的 `Copy-Item` 到 `$desktop` 会被拒（UnauthorizedAccessException），别浪费轮次。
- 只作兜底——用户常常看不见桌面文件，**优先 A / B**。

---

## 踩过的坑（照抄）

1. **`present_files` 报 Tool Not Found** → 别重复试，直接转方案 A/B/C。
2. **腾讯网盘 PUT 用 shell curl 会把 headers 里的 `&` 转义坏** → 用 Python `urllib.request`。
3. **腾讯文档端点搞混**：`tencent-docs-doc` 是 `https://docs.qq.com/api/v6/doc/mcp`，别写成 `openapi/mcp` 那条。
4. **上传响应 JSON 含 security token** → 落盘后**用完立刻 `rm`**，别留在工作区。
5. **资料库（library skill）在 `mode=client` 下可能需要 `connect_open_platform` 换票**；ToolSearch 查不到该工具时按 skill 规定**立即停止**，改走腾讯文档，别去翻 token。
6. **不要把 200 KB+ 的 markdown 直接贴进对话**——贴不下也没法读，给链接。
7. **netdrive MCP 会整组不在册**（2026-09-22 实测）：会话里用户 `@netdrive:` 引用文件时，系统只给
   `<file id="XXX" item_type="file" />` 元数据，**真去调 `netdrive__tdrive.*` 会报 not available**。
   这种情况**读不到也写不了项目盘**——别耗轮次。
   → **想拿项目盘那份的内容**：在工作区历史目录里找同名副本，`md5sum` 比对确认是同一版
   （实测三份副本 md5 完全一致 = 内容同源），拿副本继续干活。
   → **想让项目盘那份改名/更新**：做不到，只能先本地改名+改内容，把文件交付给用户，
   并明确告知"项目盘仍是旧版"，留一条待办等工具恢复。

## 配套脚本（可直接复用）

- `create_with_markdown.py`——方案 A。参数 `--mcp-url / --auth / --markdown-path / --title`。
- `nd_put.py`——方案 B 第 2 步。参数 `<响应json路径> <本地文件路径>`。

两个脚本的完整实现见创建本 skill 时的会话产物；核心都只有三四十行 `urllib` 调用。
