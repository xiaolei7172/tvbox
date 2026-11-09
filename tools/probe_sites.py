# -*- coding: utf-8 -*-
"""探测 tvbox.json 中每个源的可用性（直连优先，失败再走代理重试一次）。

判定口径：
  type 0/1 且 api 是 http URL  -> 直接请求 CMS 接口，校验返回是否为有效 JSON/XML
  其他（drpy js / py / csp_*） -> 从 ext（含 dict 形式的 site 列表）、规则文件里提域名，探站点

输出 tools/probe_result.json
"""
import json, re, os, time, warnings, threading
from concurrent.futures import ThreadPoolExecutor
import requests

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "Mozilla/5.0 (Linux; Android 11; M2007J3SC) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0 Mobile Safari/537.36"
TIMEOUT = 9
NO_PROXY = requests.Session(); NO_PROXY.trust_env = False
PROXY = requests.Session(); PROXY.trust_env = True

BAD_HOSTS = re.compile(
    r"(googletagmanager|google-analytics|jsdelivr|unpkg|cdnjs|bootcdn|staticfile|"
    r"aliyuncs|myqcloud|qiniucdn|bcebos|gitee\.com|github|githubusercontent|"
    r"w3\.org|schema\.org|example\.com|localhost|127\.0\.0\.1|0\.0\.0\.0|"
    r"fontawesome|bootstrapcdn|jquery|iview|element-ui|vuejs|"
    r"cloudflare|cloudfront|akamai|fastly|"
    r"gtimg|bdstatic|baidu\.com|sinaimg|weibo|cnzz|51\.la|umeng|doubleclick|admaster|"
    r"zhimg|jianshu|csdn|blogspot|taobao|alipay|alicdn|mmstat|google|"
    r"t\.me|telegram|youtube|ytimg|twitter|x\.com|facebook|instagram|"
    r"raw\.githubusercontent|gh-proxy|ghproxy|ghfast|wget\.la|ghps\.cc|"
    r"js\.delivr|picsum|placeholder)", re.I)


def sget(url, sess, timeout=TIMEOUT):
    return sess.get(url, timeout=timeout, verify=False, allow_redirects=True,
                    headers={"User-Agent": UA, "Accept": "*/*"})


def fetch(url):
    err = ""
    for sess in (NO_PROXY, PROXY):
        try:
            return sget(url, sess), None
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:70]}"
    return None, err


def looks_frontpage_ok(r):
    if r is None:
        return False, "无响应"
    if r.status_code == 404:
        return False, "HTTP404"
    if r.status_code >= 500:
        return False, f"HTTP{r.status_code}"
    if r.status_code in (401, 403, 429, 418):
        return True, f"HTTP{r.status_code}(反爬/Cookie墙，站点活着)"
    body = r.content or b""
    if len(body) < 150:
        return False, f"响应过短{len(body)}B"
    txt = body[:6000].decode("utf-8", "ignore").lower()
    for p in ("域名已过期", "domain for sale", "该域名出售", "网站已关闭", "站点已关闭",
              "domain expired", "account suspended", "站点未绑定", "no such app",
              "该站点已停止", "已停止访问", "域名过期", "域名解析失败", "this domain is for sale"):
        if p in txt:
            return False, f"停放/停运页"
    return True, f"HTTP{r.status_code} {len(body)}B"


def cms_probe(api):
    base = api
    joiner = "&" if "?" in base else "?"
    if re.search(r"[?&]ac=(list|videolist|detail)\b", base):
        base = re.split(r"[?&]ac=", base)[0]
        joiner = "?"
    tried = []
    for q in ("ac=list", "ac=detail&wd=%E6%B5%8B%E8%AF%95"):
        r, err = fetch(base + joiner + q)
        if r is None:
            tried.append(f"{q}:{err}")
            continue
        if r.status_code >= 400:
            tried.append(f"{q}:HTTP{r.status_code}")
            continue
        body = (r.content or b"")[:300000].decode("utf-8", "ignore").strip()
        if not body:
            tried.append(f"{q}:空响应")
            continue
        if body[0] in "{[":
            try:
                d = json.loads(body)
                n = len(d.get("list") or []) if isinstance(d, dict) else len(d)
                return True, f"CMS-JSON list={n}"
            except Exception:
                pass
        head = body[:4000]
        if re.search(r"<rss|<list|<video|<ac>|<vod>|<xml", head, re.I):
            return True, f"CMS-XML {len(body)}B"
        if "<html" in head[:1500].lower():
            tried.append(f"{q}:返回HTML")
            continue
        tried.append(f"{q}:非预期{body[:30]!r}")
    return False, " | ".join(tried[:2])


DOM_RE = re.compile(r"https?://([A-Za-z0-9][A-Za-z0-9\.\-]{2,60}\.[A-Za-z]{2,8})(?=[/:\"'\s?#,)\]\}]|$)")


def domains_in(text, limit=8):
    out, seen = [], set()
    for m in DOM_RE.finditer(text or ""):
        h = m.group(1).lower().lstrip(".")
        if BAD_HOSTS.search(h) or h in seen:
            continue
        seen.add(h)
        host = m.group(0).split("//")[-1].split("/")[0].split('"')[0].split("'")[0]
        out.append(host)
        if len(out) >= limit:
            break
    return out


def read_local(rel):
    if not rel or not isinstance(rel, str):
        return ""
    p = os.path.join(ROOT, re.sub(r"^(\./)+", "", rel))
    if not os.path.isfile(p):
        return ""
    try:
        return open(p, encoding="utf-8", errors="ignore").read()
    except Exception:
        return ""


def probe_site(s):
    api = s.get("api") or ""
    ext = s.get("ext")
    rec = {"key": s.get("key"), "name": s.get("name"), "type": s.get("type"),
           "api": str(api)[:100], "verdict": "unknown", "detail": "", "candidates": []}
    if not isinstance(api, str):
        rec["detail"] = "api 非字符串"
        return rec

    # 1) 纯 URL 接口
    if re.match(r"^https?://", api):
        rec["candidates"] = [api]
        ok, detail = cms_probe(api)
        if ok:
            rec["verdict"], rec["detail"] = "alive", detail
        else:
            host = re.sub(r"^(https?://[^/]+).*", r"\1", api)
            r, _ = fetch(host + "/")
            ok2, d2 = looks_frontpage_ok(r)
            rec["verdict"] = "alive" if ok2 else "dead"
            rec["detail"] = f"接口失效[{detail}]；首页:{d2}"
        return rec

    # 2) 收集候选域名：ext(dict/str) + 本地规则文件
    blob = ""
    if isinstance(ext, dict):
        blob += json.dumps(ext, ensure_ascii=False)
    elif isinstance(ext, str):
        blob += ext
    rule_src = ""
    if isinstance(ext, str) and ext.endswith((".js", ".json")):
        rule_src = read_local(ext)
    elif api.endswith((".py", ".js")):
        rule_src = read_local(api)
    blob += "\n" + rule_src

    cands = domains_in(blob, 8)
    rec["candidates"] = cands
    if not cands:
        rec["verdict"] = "unknown"
        rec["detail"] = "无硬编码域名（动态取域名/jar内置）"
        return rec

    notes = []
    for c in cands[:3]:
        base = c if c.startswith("http") else "https://" + c
        r, err = fetch(base)
        if r is None:
            alt = base.replace("https://", "http://", 1) if base.startswith("https") else base.replace("http://", "https://", 1)
            r, err = fetch(alt)
        ok, d = looks_frontpage_ok(r)
        notes.append(f"{c[:36]}:{d}")
        if ok:
            rec["verdict"], rec["detail"] = "alive", f"{c} {d}"
            return rec
    rec["verdict"] = "dead"
    rec["detail"] = "; ".join(notes)
    return rec


def main():
    cfg = json.loads(re.sub(r"^\s*//.*$", "", open(os.path.join(ROOT, "tvbox.json"), encoding="utf-8").read(), flags=re.M))
    sites = cfg["sites"]
    print(f"待探测 {len(sites)} 个源", flush=True)
    t0 = time.time(); done = [0]; lock = threading.Lock()

    def work(s):
        try:
            r = probe_site(s)
        except Exception as e:
            r = {"key": s.get("key"), "name": s.get("name"), "type": s.get("type"),
                 "verdict": "unknown", "detail": f"异常 {type(e).__name__}: {str(e)[:70]}", "candidates": []}
        with lock:
            done[0] += 1
            if done[0] % 50 == 0:
                print(f"  {done[0]}/{len(sites)} {round(time.time()-t0,1)}s", flush=True)
        return r

    with ThreadPoolExecutor(max_workers=32) as ex:
        res = list(ex.map(work, sites))
    json.dump(res, open(os.path.join(ROOT, "tools/probe_result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from collections import Counter
    c = Counter(r["verdict"] for r in res)
    print("结果:", dict(c), f"耗时 {round(time.time()-t0,1)}s")
    for v in ("dead",):
        print(f"\n--- {v} ({c[v]}) ---")
        for r in res:
            if r["verdict"] == v:
                print(f"  [{r['type']}] {r['name']}  |  {r['detail'][:120]}")


if __name__ == "__main__":
    main()
