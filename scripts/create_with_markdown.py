#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 MCP HTTP 接口用 Markdown 创建腾讯文档（本地直连，避开 MCP 传输体积限制）。"""
import argparse, base64, json, sys, urllib.request

SAAS_HOST = "saas.docs.qq.com"


def call_tool(mcp_url, headers, tool_name, tool_args):
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": tool_args},
        "id": 1,
    }
    req_headers = {"Content-Type": "application/json", **headers}
    req = urllib.request.Request(
        mcp_url, data=json.dumps(payload).encode("utf-8"), headers=req_headers
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        body = resp.read().decode("utf-8")
        print(body)
        try:
            if json.loads(body).get("error"):
                sys.exit(1)
        except Exception:
            pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mcp-url", default="")
    p.add_argument("--headers-json", default="")
    p.add_argument("--auth", default="")
    p.add_argument("--markdown-path", required=True)
    p.add_argument("--title", default="")
    p.add_argument("--extra-args", default="{}")
    a = p.parse_args()

    mcp_url = a.mcp_url
    is_saas = SAAS_HOST in mcp_url
    tool_name = "doc.create_with_markdown" if is_saas else "create_with_markdown"

    if a.headers_json:
        headers = json.loads(a.headers_json)
    elif a.auth:
        headers = {"Authorization": a.auth}
    else:
        print("Error: need auth", file=sys.stderr)
        sys.exit(1)

    with open(a.markdown_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    args = json.loads(a.extra_args)
    args["base64_markdown"] = b64
    if a.title:
        args["title"] = a.title

    call_tool(mcp_url=mcp_url, headers=headers, tool_name=tool_name, tool_args=args)


if __name__ == "__main__":
    main()
