# -*- coding: utf-8 -*-
import json
from collections import defaultdict, Counter

src = r"C:\Users\admin\.cursor\projects\d-myspace-skills\agent-tools\effb95b5-07fb-404d-8afd-8c8c46ce6094.txt"
out = r"D:\myspace\skills\.tmp-gitee-api-summary.md"

with open(src, encoding="utf-8") as f:
    spec = json.load(f)

paths = spec.get("paths", {})
by_tag = defaultdict(list)
token_examples = []
page_params = Counter()
no_token = []

for p, item in paths.items():
    for method, op in item.items():
        if method.startswith("x-") or method == "parameters":
            continue
        tags = op.get("tags") or ["(untagged)"]
        summary = op.get("summary") or ""
        params = list(op.get("parameters") or []) + list(item.get("parameters") or [])
        names = set()
        for pr in params:
            if not isinstance(pr, dict):
                continue
            name = pr.get("name")
            names.add(name)
            if name in ("page", "per_page", "access_token"):
                page_params[name] += 1
            if name == "access_token" and len(token_examples) < 1:
                token_examples.append(pr)
        if "access_token" not in names:
            no_token.append((method.upper(), p, summary))
        for t in tags:
            by_tag[t].append((method.upper(), p, summary))

ops = 0
by_method = Counter()
for item in paths.values():
    for m in item:
        if m != "parameters" and not str(m).startswith("x-"):
            ops += 1
            by_method[m.upper()] += 1

info = spec.get("info", {})
lines = [
    "# Gitee Open API v5 摘要",
    "",
    f"- title: {info.get('title')}",
    f"- version: {info.get('version')}",
    f"- swagger: {spec.get('swagger')}",
    f"- host: {spec.get('host')}",
    f"- basePath: {spec.get('basePath')}",
    f"- schemes: {spec.get('schemes')}",
    f"- produces: {spec.get('produces')}",
    f"- paths: {len(paths)}",
    f"- operations: {ops}",
    f"- methods: {dict(by_method)}",
    f"- definitions: {len(spec.get('definitions', {}))}",
    f"- tags: {len(spec.get('tags', []))}",
    "",
    "## access_token 参数样例",
    json.dumps(token_examples, ensure_ascii=False, indent=2),
    "",
    "## 分页/鉴权参数出现次数",
    str(dict(page_params)),
    "",
    "## 未声明 access_token 的接口",
]
for m, pth, s in no_token:
    lines.append(f"- `{m}` `{pth}` — {s}")

lines.append("")
lines.append("## 按标签的接口")
for t in sorted(by_tag.keys(), key=lambda x: -len(by_tag[x])):
    items = by_tag[t]
    lines.append("")
    lines.append(f"### {t} ({len(items)})")
    for m, pth, s in items:
        lines.append(f"- `{m}` `{pth}` — {s}")

with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("wrote", out)
print("no_token_count", len(no_token))
print(json.dumps(token_examples, ensure_ascii=False, indent=2))
