# -*- coding: utf-8 -*-
"""源体检：三路取证后给每个源定性。

  1) DNS 存在性  —— 阿里/腾讯 DoH 双解析（绕开本机 DNS 污染）。NXDOMAIN = 域名已消失。
  2) HTTP 可达性 —— 本机直连探测（tools/probe_result.json）。仅作"确认可用"的证据，
                    本机访问不了境外站，失败不作为死亡依据。
  3) 上游在册度  —— 该域名在本仓库其他配置/规则文件里被引用的文件数。0 = 无人再用。

定性规则（保守，宁留不误删）：
  dead     : DoH 双解析均 NXDOMAIN                        → 域名已死
  dead     : HTTP 确认 404/502(有真实响应) 且 上游 0 引用
  suspect  : HTTP 失败 且 上游 0 引用（但域名还在）
  alive    : HTTP 拿到有效内容，或上游 ≥1 文件仍在引用
  unknown  : 其余（jar 内置域名等，无法外证）

输出 tools/audit_result.json
"""
import json, os, re, time, warnings, threading
from concurrent.futures import ThreadPoolExecutor
import requests

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = requests.Session(); S.trust_env = False

DOH = ["https://dns.alidns.com/resolve", "https://doh.pub/dns-query"]


def doh_query(host):
    """返回 (status, ips, note)。status: 'ok' | 'nxdomain' | 'err'"""
    ans = []
    for base in DOH:
        try:
            if "doh.pub" in base:
                r = S.get(base, params={"name": host, "type": "A"},
                          headers={"accept": "application/dns-json"}, timeout=8, verify=False)
            else:
                r = S.get(base, params={"name": host, "type": "A"}, timeout=8, verify=False)
            d = r.json()
            st = d.get("Status")
            ips = [a.get("data") for a in d.get("Answer", []) if a.get("type") == 1]
            ans.append((st, ips))
        except Exception as e:
            ans.append(("err", f"{type(e).__name__}"))
    statuses = [a[0] for a in ans]
    ips = [ip for a in ans if isinstance(a[1], list) for ip in a[1]]
    if any(s == 0 for s in statuses) and ips:
        return "ok", sorted(set(ips))[:3], ""
    if any(s == 0 for s in statuses):
        return "ok", [], "仅CNAME/无A"
    if all(s == 3 for s in statuses):
        return "nxdomain", [], "双解析 NXDOMAIN"
    return "err", [], str(statuses)


def main():
    cfg = json.loads(re.sub(r"^\s*//.*$", "", open(os.path.join(ROOT, "tvbox.json"), encoding="utf-8").read(), flags=re.M))
    sites = cfg["sites"]
    probe = {r["key"]: r for r in json.load(open(os.path.join(ROOT, "tools/probe_result.json"), encoding="utf-8"))}
    corpus = json.load(open("/tmp/corpus.json", encoding="utf-8"))
    corpus = {k: [f for f in v if f not in ("tvbox.json", "tvbox-wmz.json")] for k, v in corpus.items()}
    corpus = {k: v for k, v in corpus.items() if v}

    # 收集所有候选域名
    hosts = set()
    per = {}
    for s in sites:
        p = probe.get(s["key"], {})
        hs = []
        for c in p.get("candidates", []):
            h = re.sub(r"^https?://", "", c).split("/")[0].split(":")[0].lower()
            if h and not re.match(r"^\d+\.\d+\.\d+\.\d+$", h):
                hs.append(h)
        per[s["key"]] = list(dict.fromkeys(hs))
        hosts.update(hs)
    print(f"待解析域名 {len(hosts)} 个", flush=True)

    t0 = time.time(); done = [0]; lock = threading.Lock()
    dns = {}

    def q(h):
        r = doh_query(h)
        with lock:
            done[0] += 1
            if done[0] % 100 == 0:
                print(f"  dns {done[0]}/{len(hosts)} {round(time.time()-t0,1)}s", flush=True)
        return h, r

    with ThreadPoolExecutor(max_workers=12) as ex:
        for h, r in ex.map(q, sorted(hosts)):
            dns[h] = r
    print(f"DNS 完成 {round(time.time()-t0,1)}s", flush=True)

    rows = []
    for s in sites:
        key, name = s["key"], s.get("name")
        p = probe.get(key, {})
        http_v, http_d = p.get("verdict", "unknown"), p.get("detail", "")
        hs = per.get(key, [])
        dstates = [dns.get(h, ("err", [], ""))[0] for h in hs]
        upstream = sum(len(corpus.get(h, [])) for h in hs)
        upfiles = sorted({f for h in hs for f in corpus.get(h, [])})[:3]

        if not hs:
            verdict = "unknown"
            why = "无候选域名"
        elif dstates and all(d == "nxdomain" for d in dstates):
            verdict, why = "dead", f"域名不存在（{hs[0]}）"
        elif http_v == "alive":
            verdict, why = "alive", http_d
        elif upstream > 0:
            verdict, why = "alive", f"HTTP不可达，但上游 {upstream} 处仍在引用"
        elif http_v == "dead" and any(d == "ok" for d in dstates):
            verdict, why = "suspect", f"域名在但访问失败：{http_d[:80]}；上游无人引用"
        elif any(d == "ok" for d in dstates):
            verdict, why = "unknown", f"域名在、HTTP不可达、上游无引用"
        else:
            verdict, why = "unknown", f"DNS解析异常 {dstates}"

        rows.append({"key": key, "name": name, "type": s.get("type"), "api": str(s.get("api"))[:100],
                     "http": http_v, "http_detail": http_d[:140], "dns": dict(zip(hs, dstates)),
                     "hosts": hs, "upstream": upstream, "up_files": upfiles,
                     "verdict": verdict, "why": why})

    json.dump(rows, open(os.path.join(ROOT, "tools/audit_result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    from collections import Counter
    c = Counter(r["verdict"] for r in rows)
    print("定性结果:", dict(c))
    for v in ("dead", "suspect"):
        print(f"\n=== {v} ({c[v]}) ===")
        for r in rows:
            if r["verdict"] == v:
                print(f"  [{r['type']}] {r['name']:26s} {r['why'][:90]}")


if __name__ == "__main__":
    main()
