#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把本地文件 PUT 上传到腾讯网盘（配合 tdrive.file_upload 返回的临时地址）。"""
import json, sys, urllib.request

resp = json.load(open(sys.argv[1], encoding="utf-8"))
local = sys.argv[2]

url = "https://" + resp["domain"] + resp["path"]
data = open(local, "rb").read()
req = urllib.request.Request(url, data=data, method="PUT")
for k, v in resp["headers"].items():
    req.add_header(k, v)

try:
    with urllib.request.urlopen(req, timeout=600) as r:
        print("HTTP", r.status, "bytes", len(data))
except urllib.error.HTTPError as e:
    print("HTTPError", e.code, e.read()[:500].decode("utf-8", "ignore"))
    sys.exit(1)
