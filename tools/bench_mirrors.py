#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""加速镜像测速：对每个候选地址真实拉取 tvbox.json，校验内容后统计耗时与成功率。
结果写入 bench-result.json（仓库根目录）。用法：python tools/bench_mirrors.py"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json
import statistics
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

RAW = "https://raw.githubusercontent.com/xiaolei7172/tvbox/master/tvbox.json"
GH = "gh/xiaolei7172/tvbox@master/tvbox.json"
EXPECT_SITES = 434
ATTEMPTS = 3
TIMEOUT = 12

CANDIDATES = [
    # (显示名, 类型, 地址, 前缀/改写模板)
    ("直连 raw", "直连", RAW, ""),
    ("gh-proxy.com", "前缀", "https://gh-proxy.com/" + RAW, "https://gh-proxy.com/"),
    ("ghproxy.net", "前缀", "https://ghproxy.net/" + RAW, "https://ghproxy.net/"),
    ("ghfast.top", "前缀", "https://ghfast.top/" + RAW, "https://ghfast.top/"),
    ("gh-proxy.net", "前缀", "https://gh-proxy.net/" + RAW, "https://gh-proxy.net/"),
    ("github.moeyy.xyz", "前缀", "https://github.moeyy.xyz/" + RAW, "https://github.moeyy.xyz/"),
    ("gh.llkk.cc", "前缀", "https://gh.llkk.cc/" + RAW, "https://gh.llkk.cc/"),
    ("ghproxy.cc", "前缀", "https://ghproxy.cc/" + RAW, "https://ghproxy.cc/"),
    ("cf.ghproxy.cc", "前缀", "https://cf.ghproxy.cc/" + RAW, "https://cf.ghproxy.cc/"),
    ("gh.xxooo.cf", "前缀", "https://gh.xxooo.cf/" + RAW, "https://gh.xxooo.cf/"),
    ("hub.gitmirror.com", "前缀", "https://hub.gitmirror.com/" + RAW, "https://hub.gitmirror.com/"),
    ("ghps.cc", "前缀", "https://ghps.cc/" + RAW, "https://ghps.cc/"),
    ("gh.jasonzeng.dev", "前缀", "https://gh.jasonzeng.dev/" + RAW, "https://gh.jasonzeng.dev/"),
    ("ghproxy.1888866.xyz", "前缀", "https://ghproxy.1888866.xyz/" + RAW, "https://ghproxy.1888866.xyz/"),
    ("ghfile.geekertao.top", "前缀", "https://ghfile.geekertao.top/" + RAW, "https://ghfile.geekertao.top/"),
    ("ghp.arslantu.xyz", "前缀", "https://ghp.arslantu.xyz/" + RAW, "https://ghp.arslantu.xyz/"),
    ("gh-proxy.top", "前缀", "https://gh-proxy.top/" + RAW, "https://gh-proxy.top/"),
    ("gh.7c7.cc", "前缀", "https://gh.7c7.cc/" + RAW, "https://gh.7c7.cc/"),
    ("ghproxy.cfd", "前缀", "https://ghproxy.cfd/" + RAW, "https://ghproxy.cfd/"),
    ("ghproxy.homeboyc.cn", "前缀", "https://ghproxy.homeboyc.cn/" + RAW, "https://ghproxy.homeboyc.cn/"),
    ("gcore.jsdelivr.net", "改写", f"https://gcore.jsdelivr.net/{GH}", "https://gcore.jsdelivr.net/"),
    ("testingcf.jsdelivr.net", "改写", f"https://testingcf.jsdelivr.net/{GH}", "https://testingcf.jsdelivr.net/"),
    ("fastly.jsdelivr.net", "改写", f"https://fastly.jsdelivr.net/{GH}", "https://fastly.jsdelivr.net/"),
    ("cdn.jsdelivr.net", "改写", f"https://cdn.jsdelivr.net/{GH}", "https://cdn.jsdelivr.net/"),
    ("jsd.onmicrosoft.cn", "改写", f"https://jsd.onmicrosoft.cn/{GH}", "https://jsd.onmicrosoft.cn/"),
    ("cdn.jsdmirror.com", "改写", f"https://cdn.jsdmirror.com/{GH}", "https://cdn.jsdmirror.com/"),
    ("jsdelivr.b-cdn.net", "改写", f"https://jsdelivr.b-cdn.net/{GH}", "https://jsdelivr.b-cdn.net/"),
    ("cdn.statically.io", "改写", "https://cdn.statically.io/gh/xiaolei7172/tvbox/master/tvbox.json", "https://cdn.statically.io/gh/"),
    ("raw.githack.com", "改写", "https://raw.githack.com/xiaolei7172/tvbox/master/tvbox.json", "https://raw.githack.com/"),
]


def fetch_once(url):
    cmd = ["curl", "-sL", "--noproxy", "*", "-k", "--max-time", str(TIMEOUT),
           "-A", "Mozilla/5.0", "-o", "-", "-w", "\n__META__%{http_code} %{size_download} %{time_total} %{time_starttransfer}",
           url]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT + 8)
        out = p.stdout
        idx = out.rfind(b"\n__META__")
        if idx < 0:
            return {"ok": False, "why": "无响应", "secs": round(time.time() - t0, 2)}
        body = out[:idx]
        code, size, total, ttfb = out[idx + 9:].decode().split()
        code, size = int(code), int(size)
        total, ttfb = float(total), float(ttfb)
        if code != 200:
            return {"ok": False, "why": f"HTTP {code}", "secs": round(total, 2)}
        if size != len(body):
            return {"ok": False, "why": f"长度不符 {len(body)}", "secs": round(total, 2)}
        try:
            d = json.loads(body)
        except Exception:
            snippet = body[:40].decode("utf-8", "ignore")
            return {"ok": False, "why": f"非 JSON（{snippet[:24]}）", "secs": round(total, 2)}
        if len(d.get("sites", [])) != EXPECT_SITES:
            return {"ok": False, "why": f"站数 {len(d.get('sites', []))}", "secs": round(total, 2)}
        return {"ok": True, "secs": round(total, 3), "ttfb": round(ttfb, 3),
                "size": size, "kbps": round(size / 1024 / max(total, 0.001), 1)}
    except subprocess.TimeoutExpired:
        return {"ok": False, "why": "超时", "secs": round(time.time() - t0, 2)}
    except Exception as e:
        return {"ok": False, "why": type(e).__name__, "secs": round(time.time() - t0, 2)}


def bench(item):
    name, kind, url, prefix = item
    runs = [fetch_once(url) for _ in range(ATTEMPTS)]
    good = [r for r in runs if r["ok"]]
    med = round(statistics.median([r["secs"] for r in good]), 2) if good else None
    ttfb = round(statistics.median([r["ttfb"] for r in good]), 2) if good else None
    kbps = round(statistics.median([r["kbps"] for r in good]), 0) if good else None
    why = "" if good else (runs[0].get("why") or "失败")
    if good and len(good) < ATTEMPTS:
        why = "偶发失败"
    return {"name": name, "kind": kind, "url": url, "prefix": prefix,
            "rate": f"{len(good)}/{ATTEMPTS}", "ok": len(good),
            "median": med, "ttfb": ttfb, "kbps": kbps, "why": why,
            "runs": [r.get("why", "ok") for r in runs]}


def main():
    print(f"测速中：{len(CANDIDATES)} 个地址 × {ATTEMPTS} 次 …", flush=True)
    with ThreadPoolExecutor(max_workers=5) as ex:
        rows = list(ex.map(bench, CANDIDATES))
    # 排序：可用数降序 → 中位耗时升序
    rows.sort(key=lambda r: (-r["ok"], r["median"] if r["median"] else 9999))
    for i, r in enumerate(rows, 1):
        t = f"{r['median']:.2f}s" if r["median"] else "—"
        k = f"{r['kbps']:.0f} KB/s" if r["kbps"] else "—"
        print(f"{i:2d}. {r['name']:24s} {r['rate']:5s} {t:>7s} {k:>11s}  {r['kind']}  {r['why']}")
    json.dump(rows, open(os.path.join(ROOT, "bench-result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("\n已写入 bench-result.json")


if __name__ == "__main__":
    main()
