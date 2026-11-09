#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TVBox 仓库自检工具
====================
用于 xiaolei7172/tvbox 及同类 TVBox 配置仓库的日常健康检查。

检查项：
  1. 文件构成与体积分布
  2. JSON 合法性（区分：严格合法 / JSONC 宽松 / 真损坏）
  3. TVBox 配置结构（sites / lives / parses 完整性）
  4. 本地引用完整性（jar / js / py / json，支持 $$$ 多参语法）
  5. spider 声明 MD5 与 jar 实际 MD5 一致性（TVBox 强校验项）
  6. 重复文件（MD5 相同）
  7. 敏感信息（Cookie / Token / 密码 / 私钥）
  8. 文件名风险（空格 / 仅大小写不同）
  9. Python 脚本语法

用法：
    python tools/check_health.py             # 人类可读报告
    python tools/check_health.py --json      # 机器可读 JSON
    python tools/check_health.py --no-secret # 跳过敏感信息扫描（更快）

退出码：
    0 = 无 P0 问题
    1 = 存在 P0 问题（配置不可用级别）
"""
import os
import re
import sys
import json
import hashlib
import argparse
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".vscode"}
LOCAL_EXTS = (".jar", ".js", ".py", ".json", ".txt", ".m3u")
CFG_KEYS = {"sites", "lives", "parses", "rule", "ijk", "ads", "flags", "wallpaper", "spider"}

SECRET_PATTERNS = [
    (re.compile(r"(?i)\b(token|access_token|refresh_token|opentoken)\b\s*[\"']?\s*[:=]\s*[\"']([A-Za-z0-9_\-.]{16,})"), "token"),
    (re.compile(r"(?i)\bcookie\b\s*[\"']?\s*[:=]\s*[\"']([^\"'\n]{20,})"), "cookie"),
    (re.compile(r"(?i)\bSESSDATA\s*=\s*([^;\"'\s]{20,})"), "bilibili-sessdata"),
    (re.compile(r"(?i)\b(password|passwd|pwd)\b\s*[\"']?\s*[:=]\s*[\"']([^\"'\n]{4,})"), "password"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"), "github-token"),
    (re.compile(r"BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY"), "private-key"),
]


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


def walk_files():
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            out.append(os.path.join(dirpath, fn))
    return out


def strip_jsonc(text):
    """去除 // 与 /* */ 注释及尾逗号，使 JSONC 可被标准解析器读取。"""
    out, i, n = [], 0, len(text)
    in_str = esc = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(c)
        i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def load_jsonc(path):
    raw = open(path, "rb").read().decode("utf-8-sig")
    try:
        return json.loads(raw), "strict"
    except Exception:
        return json.loads(strip_jsonc(raw)), "jsonc"


_md5_cache = {}


def md5(path):
    if path not in _md5_cache:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        _md5_cache[path] = h.hexdigest()
    return _md5_cache[path]


def is_remote(s):
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", s or ""))


def is_clan(s):
    return (s or "").startswith("clan://") or (s or "").startswith("data:")


def resolve_local(ref, src):
    """返回 (状态, 解析结果)：'ok' / 'miss' / 'skip'"""
    r = ref.split("#")[0].split("?")[0].strip()
    if not r.lower().endswith(LOCAL_EXTS):
        return "skip", None
    base = os.path.dirname(src)
    # 配置中的中文路径可能是 percent-encoding，需先尝试 %XX 解码
    variants = [r]
    if "%" in r:
        try:
            from urllib.parse import unquote
            variants.append(unquote(r))
        except Exception:
            pass
    for v in variants:
        if not v.lower().endswith(LOCAL_EXTS):
            continue
        for cand in (os.path.normpath(os.path.join(base, v)),
                     os.path.normpath(os.path.join(ROOT, v.lstrip("./")))):
            if os.path.exists(cand):
                return "ok", cand
    return "miss", r


def looks_like_secret(tag, sample, path=""):
    """剔除明显的误报：本地路径引用、占位符、第三方加密库自带的测试密钥。"""
    low = sample.lower()
    # 指向本地文件 / clan:// / 回环地址的 cookie 字段是路径引用，不是凭证
    if tag in ("cookie", "password"):
        for marker in ("clan://", "127.0.0.1", "localhost", "./", "http://", "https://"):
            if marker in low and "=" not in low.split(marker, 1)[-1]:
                return False
        if tag == "password":
            val = sample.split(":")[-1].strip(" \"'")
            if val in {"agree", "", "true", "false", "[type=password]"}:
                return False
    # 第三方加密库内置的示例/测试密钥，非泄漏
    if tag == "private-key":
        base = os.path.basename(path).lower()
        for lib in ("node-rsa", "jsencrypt", "crypto", "drpy", "cloud.min", "quark.min", "cheerio"):
            if lib in base:
                return False
    # 占位符
    if "xxxxxxx" in low:
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--no-secret", action="store_true", help="跳过敏感信息扫描")
    args = ap.parse_args()

    files = walk_files()
    report = {"root": ROOT, "files": len(files), "p0": [], "p1": [], "p2": []}

    # ---------- 1. 体积分布 ----------
    ext = defaultdict(lambda: [0, 0])
    for p in files:
        e = os.path.splitext(p)[1].lower() or "(none)"
        ext[e][0] += 1
        ext[e][1] += os.path.getsize(p)
    report["by_ext"] = {k: {"count": v[0], "bytes": v[1]} for k, v in
                        sorted(ext.items(), key=lambda x: -x[1][1])}

    # ---------- 2/3. JSON ----------
    strict = jsonc = broken = 0
    broken_list, jsonc_list, configs = [], [], []
    for p in files:
        if not p.lower().endswith(".json"):
            continue
        try:
            data, kind = load_jsonc(p)
        except Exception as ex:
            broken += 1
            broken_list.append({"file": rel(p), "error": str(ex)[:120]})
            continue
        if kind == "strict":
            strict += 1
        else:
            jsonc += 1
            jsonc_list.append(rel(p))
        if isinstance(data, dict) and (set(data) & CFG_KEYS):
            sites = data.get("sites") if isinstance(data.get("sites"), list) else []
            configs.append({
                "file": rel(p),
                "sites": len(sites),
                "lives": len(data.get("lives") or []) if isinstance(data.get("lives"), list) else 0,
                "parses": len(data.get("parses") or []) if isinstance(data.get("parses"), list) else 0,
                "spider": data.get("spider") or "",
                "_data": data,
            })
    report["json"] = {"strict": strict, "jsonc": jsonc, "broken": broken,
                      "broken_files": broken_list, "jsonc_files": jsonc_list}
    if broken:
        report["p0"].append(f"{broken} 个 JSON 文件无法解析")

    # ---------- 4. 本地引用 ----------
    refs_ok, refs_miss = 0, []
    for cfg in configs:
        data = cfg["_data"]
        src = os.path.join(ROOT, cfg["file"])
        pairs = []
        if data.get("spider"):
            pairs.append(("spider", data["spider"]))
        for sec in ("sites", "lives", "parses", "ijk", "ads", "wallpaper", "flags"):
            v = data.get(sec)
            if not isinstance(v, list):
                continue
            for i, it in enumerate(v):
                if isinstance(it, dict):
                    for k in ("api", "jar", "ext", "logo", "spider", "js", "url"):
                        if it.get(k):
                            pairs.append((f"{sec}[{i}].{k}", it[k]))
                elif isinstance(it, str):
                    pairs.append((f"{sec}[{i}]", it))
        for tag, val in pairs:
            for part in str(val).split("$$$"):
                part = part.strip()
                if not part or is_remote(part) or is_clan(part) or part.startswith("csp_"):
                    continue
                st, r = resolve_local(part, src)
                if st == "ok":
                    refs_ok += 1
                elif st == "miss":
                    refs_miss.append({"file": cfg["file"], "field": tag, "ref": r})
    report["refs"] = {"ok": refs_ok, "missing": refs_miss}
    if refs_miss:
        # 断链通常源于上游删改规则文件，属功能降级而非配置不可用，
        # 因此归入 P1；spider 文件缺失才是 P0（见下一节）。
        report["p1"].append(f"{len(refs_miss)} 处本地引用断链")

    # ---------- 5. spider MD5 ----------
    spider_rows = []
    for cfg in configs:
        sp = cfg["spider"]
        if not sp:
            continue
        parts = sp.split(";")
        path = parts[0]
        decl = parts[2] if len(parts) >= 3 and parts[1].lower() == "md5" else None
        row = {"file": cfg["file"], "path": path, "declared": decl}
        if is_remote(path):
            row["status"] = "remote"
            spider_rows.append(row)
            continue
        src = os.path.join(ROOT, cfg["file"])
        st, real = resolve_local(path, src)
        if st != "ok":
            row["status"] = "missing"
            spider_rows.append(row)
            report["p0"].append(f"{cfg['file']} 的 spider 文件不存在：{path}")
            continue
        actual = md5(real)
        row["actual"] = actual
        if decl is None:
            row["status"] = "no-check"
        elif decl.lower() == actual:
            row["status"] = "ok"
        else:
            row["status"] = "mismatch"
            spider_rows.append(row)
            report["p0"].append(f"{cfg['file']} 的 spider MD5 不匹配（声明 {decl[:8]}… 实际 {actual[:8]}…）")
            continue
        spider_rows.append(row)
    report["spider"] = spider_rows

    # ---------- 6. 重复 ----------
    groups = defaultdict(list)
    for p in files:
        if os.path.getsize(p) > 8 * 1024 * 1024:
            continue
        try:
            groups[md5(p)].append(rel(p))
        except Exception:
            pass
    dups = [v for v in groups.values() if len(v) > 1]
    report["duplicates"] = dups

    # ---------- 7. 敏感信息 ----------
    secrets = []
    if not args.no_secret:
        for p in files:
            e = os.path.splitext(p)[1].lower()
            if e not in {".json", ".js", ".py", ".txt", ".m3u", ".yml", ".yaml", ".md", ""}:
                continue
            if os.path.getsize(p) > 4 * 1024 * 1024:
                continue
            try:
                t = open(p, "rb").read().decode("utf-8", "ignore")
            except Exception:
                continue
            for rx, tag in SECRET_PATTERNS:
                # JS/库代码里 `cookie = "..."` 多为变量拼接，误报率高；
                # 仅对 JSON/配置类文件做通用 Cookie 检测。
                if e in {".js", ".py"} and tag in ("cookie", "password"):
                    continue
                for m in rx.finditer(t):
                    snip = m.group(0)[:90].replace("\n", " ")
                    if not looks_like_secret(tag, snip, p):
                        continue
                    secrets.append({"file": rel(p), "type": tag, "sample": snip})
        seen, uniq = set(), []
        for s in secrets:
            k = (s["file"], s["type"], s["sample"][:40])
            if k not in seen:
                seen.add(k)
                uniq.append(s)
        secrets = uniq
    report["secrets"] = secrets
    if secrets:
        report["p1"].append(f"{len(set(s['file'] for s in secrets))} 个文件含疑似凭证")

    # ---------- 8. 文件名 ----------
    spaces = [rel(p) for p in files if " " in os.path.basename(p)]
    lm = defaultdict(list)
    for p in files:
        lm[rel(p).lower()].append(rel(p))
    coll = {k: v for k, v in lm.items() if len(v) > 1}
    report["naming"] = {"with_space": spaces, "case_collision": coll}

    # ---------- 9. Python 语法 ----------
    bad_py = []
    for p in files:
        if not p.endswith(".py"):
            continue
        try:
            compile(open(p, "rb").read().decode("utf-8-sig"), p, "exec")
        except Exception as ex:
            bad_py.append({"file": rel(p), "error": f"{type(ex).__name__}: {ex}"})
    report["python"] = {"broken": bad_py}

    # ---------- 输出 ----------
    if args.json:
        for c in configs:
            c.pop("_data", None)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if report["p0"] else 0

    W = 78
    def line(title):
        print("\n" + "=" * W)
        print(title)
        print("=" * W)

    print(f"TVBox 仓库体检 · {ROOT}")
    print(f"文件数 {len(files)}")
    line("【1】体积分布")
    for e, v in report["by_ext"].items():
        print(f"  {e:<12}{v['count']:>6} 个{v['bytes']/1048576:>10.2f} MB")

    line("【2】JSON 合法性")
    print(f"  严格合法 {strict}    JSONC 宽松 {jsonc}    真损坏 {broken}")
    for b in broken_list:
        print(f"  [X] {b['file']}\n      {b['error']}")

    line("【3】配置结构（sites / lives / parses）")
    for c in sorted(configs, key=lambda x: -x["sites"]):
        sp = c["spider"]
        sp = sp[:40] + "…" if len(sp) > 40 else sp
        print(f"  {c['file']:<26}{c['sites']:>5}{c['lives']:>6}{c['parses']:>6}   {sp}")

    line("【4】本地引用完整性")
    print(f"  可解析 {refs_ok} 处 / 断链 {len(refs_miss)} 处")
    for m in refs_miss:
        print(f"  [X] {m['file']}  ({m['field']})  ->  {m['ref']}")

    line("【5】spider MD5 校验")
    mark = {"ok": " OK ", "mismatch": "[!!]", "missing": "[X ]", "remote": " -- ", "no-check": " ~  "}
    bad = 0
    for r in spider_rows:
        if r["status"] in ("mismatch", "missing"):
            bad += 1
        print(f"{mark[r['status']]} {r['file']:<24}{r['path'][:34]:<36}"
              f"{r['status']}")
        if r["status"] == "mismatch":
            print(f"        声明 {r['declared']}")
            print(f"        实际 {r['actual']}")
    print(f"\n  异常 {bad} 处")

    line("【6】重复文件")
    print(f"  重复组 {len(dups)} 组")
    for g in dups[:60]:
        print("  ==  " + "   ".join(g))
    if len(dups) > 60:
        print(f"  … 另有 {len(dups)-60} 组，详见 --json 输出")

    if not args.no_secret:
        line("【7】敏感信息")
        if secrets:
            for s in secrets:
                print(f"  [{s['type']}] {s['file']}")
                print(f"        {s['sample']}")
        else:
            print("  未发现")

    line("【8】文件名风险")
    print(f"  含空格 {len(spaces)} 个")
    print(f"  仅大小写不同 {len(coll)} 组（Windows/macOS 克隆会丢文件）")
    for k, v in coll.items():
        print("    " + "  vs  ".join(v))

    line("【9】Python 语法")
    print(f"  语法错误 {len(bad_py)} 个")
    for b in bad_py:
        print(f"  [X] {b['file']}: {b['error']}")

    line("结论")
    if report["p0"]:
        print("  P0（影响可用性）：")
        for m in report["p0"]:
            print(f"    ✗ {m}")
    else:
        print("  P0：无")
    if report["p1"]:
        print("  P1（需关注）：")
        for m in report["p1"]:
            print(f"    ! {m}")
    print()
    return 1 if report["p0"] else 0


if __name__ == "__main__":
    sys.exit(main())
