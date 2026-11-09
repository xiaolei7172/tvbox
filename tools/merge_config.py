# -*- coding: utf-8 -*-
"""
把仓库内 13 个配置合并成一份 TVBox 可直接使用的多仓配置。

设计原则
--------
1. 单一 spider：只能选一个 jar。选 ./jar/spider.jar（FongMi 官方，1.85MB），
   因为 jsm / dianshi / xiaosa 三个配置都用它，且它的 csp_ 覆盖面最广。
2. csp_ 站点只保留白名单内的前缀 —— 白名单来自「同样用 spider.jar 的那三个配置」，
   这是「spider.jar 一定认识这个类」的可靠证据。
3. js / py / http 三类站点与 jar 无关（客户端各自有运行时），全部收进来。
4. key 与 name 双去重；ext 断链的站点剔除。
5. 骨架（hosts/flags/doh/rules/ads/wallpaper/danmaku）取 jsm.json，最完整。
"""
import os
import re
import sys
import json
from collections import Counter, OrderedDict
from urllib.parse import unquote  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")


def strip_jsonc(t):
    out, i, n = [], 0, len(t)
    ins = esc = False
    while i < n:
        c = t[i]
        if ins:
            out.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                ins = False
            i += 1
            continue
        if c == '"':
            ins = True
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and t[i + 1] == "/":
            while i < n and t[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and t[i + 1] == "*":
            i += 2
            while i + 1 < n and not (t[i] == "*" and t[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(c)
        i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def load(f):
    p = os.path.join(ROOT, f)
    if not os.path.exists(p):
        return None
    return json.loads(strip_jsonc(open(p, encoding="utf-8-sig").read()))


def load_wmz():
    """
    读 sources/wmz.txt。该文件是 wmz 订阅源的原样快照：
    前缀 YmFzZTY0** 之后是整段 base64，解出来才是配置 JSON。
    保持原样存放，便于随时用 curl 覆盖刷新。
    """
    import base64
    p = os.path.join(ROOT, "sources", "wmz.txt")
    if not os.path.exists(p):
        print("[!] 未找到 sources/wmz.txt，跳过 wmz 源")
        return None
    t = open(p, encoding="utf-8").read().strip()
    marker = "YmFzZTY0**"
    body = t[len(marker):] if t.startswith(marker) else t
    body += "=" * (-len(body) % 4)
    try:
        return json.loads(base64.b64decode(body).decode("utf-8"))
    except Exception as e:
        print(f"[!] wmz 解码失败：{e}")
        return None


def norm_name(n):
    """
    站点名的语义归一化，用于跨配置去重。
    不同配置给同一个源起名风格差异极大：
        「快映 • 4K」 vs 「💯快映｜4K臻享」
    去掉符号后逐层剥掉营销后缀，两边就都收敛成「快映」。
    只剥一层不动中间词，避免把「哔哩 • 音乐」和「哔哩 • 资源」误判成同一个。
    """
    s = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", str(n or ""))
    for _ in range(3):
        s2 = re.sub(r"(蓝光|秒播|臻享|臻彩|网盘|影视|资源|合集|搜索|直播|专区|剧场)$", "", s)
        if s2 == s:
            break
        s = s2
    return s.lower()


# ── 1. 读入 ────────────────────────────────────────────────────────────────
BASE = "jsm.json"          # 骨架 + 主站点来源
SAME_JAR = ["jsm.json", "dianshi.json", "xiaosa/api.json"]   # 同用 spider.jar
EXTRA = ["js.json", "0821.json", "0825.json", "0826.json",
         "0827.json", "9918.json", "99188.json", "XYQ.json", "367.json", "fty.json"]

SPIDER_JAR = os.path.join(ROOT, "jar", "spider.jar")


def dex_classes(jar_path):
    """
    从 jar 的 classes.dex 中提取 spider 类名。
    dex 里的类名以明文 MUTF-8 存储（形如 Lcom/github/catvod/spider/Bili;），
    因此可以绕过反编译直接拿到「这个 jar 支持哪些 csp_ 类」的权威清单。
    """
    import zipfile
    with zipfile.ZipFile(jar_path) as z:
        blob = b"".join(z.read(n) for n in z.namelist() if n.endswith(".dex"))
    return {m.group(1).decode("ascii")
            for m in re.finditer(rb"com/github/catvod/spider/([A-Za-z0-9]{2,40})", blob)}


base = load(BASE)
SPIDER = base["spider"]
print(f"基座 spider : {SPIDER}")

# ── 2. csp_ 白名单：直接从基座 jar 的 dex 提取 ──────────────────────────────
#
# 对比（同一批 13 个配置、去重后能收的站点数）：
#   spider.jar        122 类 → 496 个   ← 覆盖最广，且仅 1.85 MB
#   pg_upgraded.jar   132 类 → 450 个   （类更多，但与 spider.jar 几乎不重叠，
#                                        缺 XBPQ / XYQHiker / PanWebShare / Sports* 等大项）
#   pg23a94bb.jar     128 类 → 451 个   （11.18 MB，体积代价过高）
#   XYQ.jar / custom_spider.jar / fan.txt → 382 / 369 / 371
#
whitelist = dex_classes(SPIDER_JAR)
print(f"csp_ 白名单 : {len(whitelist)} 类（从 {os.path.basename(SPIDER_JAR)} 的 dex 提取）")

# ── 3. 收集站点 ────────────────────────────────────────────────────────────
LOCAL_EXTS = (".jar", ".js", ".py", ".json", ".txt", ".m3u")


def resolve_ok(ref):
    """检查配置内相对路径是否存在（处理 %XX 编码）"""
    from urllib.parse import unquote
    r = str(ref).split("#")[0].split("?")[0].strip()
    cands = [r]
    if "%" in r:
        cands.append(unquote(r))
    for v in cands:
        if not v.lower().endswith(LOCAL_EXTS):
            return True
        for c in (os.path.normpath(os.path.join(ROOT, v.lstrip("./"))),
                  os.path.normpath(os.path.join(ROOT, v))):
            if os.path.exists(c):
                return True
    return False


def ext_broken(site):
    """站点 ext 是否为本地路径且文件缺失"""
    for key in ("ext", "api"):
        v = site.get(key)
        if isinstance(v, str) and v and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", v):
            if v.startswith("csp_") or v.startswith("clan://"):
                continue
            for part in v.split("$$$"):
                part = part.strip()
                if not part:
                    continue
                if not resolve_ok(part):
                    return True
    return False


# 黑名单：tools/blocklist.txt 里登记的 key 一律不入表（死链 / 重复源）。
BLOCK_PATH = os.path.join(ROOT, "tools", "blocklist.txt")
BLOCK = set()
if os.path.isfile(BLOCK_PATH):
    for line in open(BLOCK_PATH, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        BLOCK.add(line.split("\t")[0].split()[0])
print(f"黑名单：{len(BLOCK)} 条（{os.path.relpath(BLOCK_PATH, ROOT)}）")

kept, dropped = [], []
keys, names = set(), set()
norms = set()                      # 归一化名称，跨配置语义去重
pairs = set()                      # (api, ext)，同一规则被重复收录
stat = Counter()

# 这些类的 ext 只是登录态文件，真正区分站点内容的是 name
# （「哔哩｜音乐」和「哔哩｜相声」共用同一个 cookie 文件）。
# 对它们禁用 (api,ext) 去重，否则会把不同分区误合并。
NAME_DISTINGUISHED = {"csp_Bili", "csp_BiliYS"}


def add_sites(src_name, sites, allow_csp=False, forbid_csp=False, cross_dedup=False):
    """
    cross_dedup=True 时启用「跨配置语义去重」：
    按归一化名称 + (api, ext) 判断是否已有等价站点。
    只给 wmz 这种「来自另一套命名体系」的源打开 —— 仓库内原有 13 个配置
    彼此 key/name 体系一致，直接按 key/name 去重就够；对它们启用归一化
    判断反而会把「本地视频」「爱看」这类本来合法的站误判成重复。
    """
    for s in sites:
        if not isinstance(s, dict):
            continue
        api = str(s.get("api") or "")
        k, nm = s.get("key"), s.get("name")
        if not k or not nm:
            stat[f"{src_name}:缺key/name"] += 1
            continue
        if not api:
            stat[f"{src_name}:无api"] += 1
            continue
        if api.startswith("csp_"):
            if forbid_csp:
                stat[f"{src_name}:csp不兼容"] += 1
                continue
            if api[4:] not in whitelist:
                stat[f"{src_name}:csp不在白名单"] += 1
                continue
        if k in keys:
            stat[f"{src_name}:key重复"] += 1
            continue
        if k in BLOCK:
            stat[f"{src_name}:黑名单"] += 1
            continue
        if nm in names:
            stat[f"{src_name}:name重复"] += 1
            continue
        nn = norm_name(nm)
        ext_s = json.dumps(s["ext"], sort_keys=True, ensure_ascii=False) if isinstance(s.get("ext"), (dict, list)) else str(s.get("ext") or "")
        pair = (api, ext_s)
        if cross_dedup:
            if nn and nn in norms:
                stat[f"{src_name}:同名异写"] += 1
                continue
            if ext_s and pair in pairs and api not in NAME_DISTINGUISHED:
                stat[f"{src_name}:同源重复"] += 1
                continue
        if ext_broken(s):
            stat[f"{src_name}:ext断链"] += 1
            dropped.append((src_name, nm, s.get("ext")))
            continue
        keys.add(k)
        names.add(nm)
        if nn:
            norms.add(nn)
        if ext_s:
            pairs.add(pair)
        kept.append(s)
        stat[f"{src_name}:收录"] += 1


# 3.1 同 spider 的三个配置：全部允许
for f in SAME_JAR:
    d = load(f)
    if d:
        add_sites(f, d.get("sites") or [], allow_csp=True)
        print(f"  {f:<18} 累计 {len(kept)}")

# 3.2 其余配置：csp_ 走白名单，js/py/http 全收
for f in EXTRA:
    d = load(f)
    if not d:
        continue
    add_sites(f, d.get("sites") or [], allow_csp=False)
    print(f"  {f:<18} 累计 {len(kept)}")

# 3.3 wmz 源（外部订阅，自带 261109.jar）
# 它 95 个站里有 79 个的 csp_ 类同样在 spider.jar 内，可直接并入；
# 剩下 16 个依赖 261109.jar 独有类（AList/Pan115/WebDAV/Libvio 等），
# 只能留在 tvbox-wmz.json 那份用它自己 jar 的配置里。
WMZ = load_wmz()
if WMZ:
    add_sites("wmz", WMZ.get("sites") or [], allow_csp=False, cross_dedup=True)
    print(f"  {'wmz':<18} 累计 {len(kept)}")

print(f"\n站点合计 {len(kept)}，剔除 {sum(v for k, v in stat.items() if '收录' not in k)}")

# ── 4. 合并 lives（URL 规范化去重）────────────────────────────────────────
def norm_url(u):
    """用于判重的规范化：去协议差异、去尾部斜杠、统一小写主机"""
    s = str(u or "").strip()
    s = re.sub(r"^https?://", "//", s, flags=re.I)
    s = s.rstrip("/")
    return s.lower()


def all_sources():
    """按优先级产出 (名称, 配置对象)，主配置在前、wmz 垫底"""
    for f in SAME_JAR + EXTRA:
        d = load(f)
        if d:
            yield f, d
    if WMZ:
        yield "wmz", WMZ


LOCAL_LIVE = re.compile(r"^\./([\w\-./]+\.(?:txt|m3u))$", re.I)


def live_urls(u):
    """把本地直播文件读成 URL 集合，用来判断两个直播源是不是同一份列表"""
    m = LOCAL_LIVE.match(str(u or ""))
    if not m or not os.path.isfile(m.group(1)):
        return None
    urls = set()
    try:
        with open(m.group(1), encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.endswith("#genre#"):
                    continue
                if line.startswith("http"):
                    urls.add(line)
                elif "," in line and not line.startswith("#"):
                    tail = line.rsplit(",", 1)[-1].strip()
                    if tail.startswith("http"):
                        urls.add(tail)
    except OSError:
        return None
    return urls or None


lives, seen_live, live_sets = [], set(), []   # live_sets: [(index, ext, urlset)]
dropped_live = []
for f, d in all_sources():
    for lv in d.get("lives") or []:
        if not isinstance(lv, dict):
            continue
        u = str(lv.get("url") or "")
        if not u:
            continue
        n = norm_url(u)
        if n in seen_live:
            continue
        if not resolve_ok(u):
            continue

        # 同格式的本地直播源：URL 重合 ≥95% 视为同一份列表，只留频道多的那份
        cur = live_urls(u)
        if cur:
            ext = os.path.splitext(u)[1].lower()
            same = next((x for x in live_sets
                         if x[1] == ext and len(cur & x[2]) >= 0.95 * min(len(cur), len(x[2]))), None)
            if same:
                idx, _, old = same
                if len(cur) > len(old):
                    dropped_live.append((lives[idx].get("name"), lives[idx].get("url"), u))
                    lives[idx] = lv
                    live_sets.remove(same)
                    live_sets.append((idx, ext, cur))
                    seen_live.add(n)
                else:
                    dropped_live.append((lv.get("name"), u, lives[idx].get("url")))
                continue
            live_sets.append((len(lives), ext, cur))

        seen_live.add(n)
        lives.append(lv)

# 同名直播源加后缀区分（客户端列表靠名字区分，重名等于看不见）
_name_cnt = Counter(str(x.get("name") or "") for x in lives)
_seen_name = Counter()
for lv in lives:
    nm = str(lv.get("name") or "")
    if _name_cnt[nm] > 1:
        _seen_name[nm] += 1
        tag = os.path.splitext(str(lv.get("url") or "").split("?")[0])[1].lstrip(".").upper()
        lv["name"] = f"{nm}•{tag or _seen_name[nm]}"

for a, b, keep in dropped_live:
    print(f"  直播去重：{a} ({b}) 与 {keep} 为同一份列表，丢弃")

# ── 5. 合并 parses（清洗无效项）──────────────────────────────────────────
parses, seen_parse, seen_pname = [], set(), Counter()
for f, d in all_sources():
    for ps in d.get("parses") or []:
        if not isinstance(ps, dict):
            continue
        u = str(ps.get("url") or "").strip()
        if not u or u.lower() in {"demo", "null", "none"}:
            continue
        # 同一接口只留一条：名字不同（如「虾米」「-虾米-」）实为同一个 url
        sig = (norm_url(u), ps.get("type"))
        if sig in seen_parse:
            continue
        seen_parse.add(sig)
        nm = str(ps.get("name") or "")
        seen_pname[nm] += 1
        if seen_pname[nm] > 1:      # 同名不同接口，加序号避免客户端里认不出
            ps["name"] = f"{nm}{seen_pname[nm]}"
        parses.append(ps)

print(f"直播源 {len(lives)} 个，解析 {len(parses)} 个")

# ── 5.4 失效加速站本地化 ──────────────────────────────────────────────────
# gh-proxy.net 已被劫持：返回的是「window.location.replace(...)」跳转页而不是文件内容；
# github.moeyy.xyz 已无 DNS 记录（NXDOMAIN）。
# 这几个站点的 api（drpy2 引擎）和 ext（规则）都挂在这两个域名上，整条链路是断的，
# 在电视上表现为「点开就报错 / 一直转圈」。改成仓库自带的 lib/ 引擎 + 本地规则文件。
DEAD_PROXY = ("https://gh-proxy.net/", "https://github.moeyy.xyz/")
LOCAL_RULE = {
    # 仓库里本来就有的同名规则（FTY / js），直接指向它们，不重复上架
    "有声小说吧.js": "FTY/有声小说吧.js",
    "兔小贝.js":     "FTY/兔小贝.js",
    "jrk.js":        "FTY/jrk.js",
    "斗鱼直播.js":    "FTY/斗鱼直播.js",
    "酷奇MV.js":      "js/酷奇MV.js",
    "去看吧.js":      "js/去看吧.js",
    # 上游这份是 **base64 混淆的，这里放了明文版本，兼容性最好
    "huya2.js":      "js/ext/huya2.js",
}
_relocalized, _leftover = 0, []
for s in kept:
    hit = False
    for field in ("api", "ext"):
        v = s.get(field)
        if not (isinstance(v, str) and v.startswith(DEAD_PROXY)):
            continue
        fname = unquote(v.rsplit("/", 1)[-1])
        if field == "api":
            s[field] = "./lib/drpy2.js" if fname == "drpy2.js" else "./lib/drpy2.min.js"
            hit = True
        else:
            rel = LOCAL_RULE.get(fname)
            if rel and os.path.isfile(rel):
                s[field] = "./" + rel
                hit = True
            else:
                _leftover.append((s.get("name"), v))
    if hit:
        _relocalized += 1

if _relocalized:
    print(f"本地化 {_relocalized} 个站点：失效加速站的引擎/规则 → ./lib + ./js")
for n, u in _leftover:
    print(f"  ! 未本地化（缺规则文件）：{n} → {u[:70]}")

# 本地化之后，原本「远程地址不同、实际是同一份规则」的站点会合并成同一条，
# 这里再按 (api, ext) 去一次重，避免列表里出现两个一模一样的小图标。
_sig, _uniq, _merged = set(), [], []
for s in kept:
    k = (json.dumps(s.get("api"), sort_keys=True, ensure_ascii=False),
         json.dumps(s.get("ext"), sort_keys=True, ensure_ascii=False))
    if k in _sig:
        _merged.append(s.get("name"))
        continue
    _sig.add(k)
    _uniq.append(s)
if _merged:
    kept = _uniq
    print(f"规则同源合并 −{len(_merged)}：{'、'.join(str(x) for x in _merged)}")

# ── 5.5 站点分组排序 ──────────────────────────────────────────────────────
# 客户端按 sites 数组顺序渲染列表，排序直接决定观感。
# 保持 name 原样（不篡改用户认知），仅调整顺序。
# 序号 1 留给「影视」兜底组，让点播主体紧跟在工具箱之后。
GROUPS = [
    ("工具箱", 0, ("搜索", "配置", "本地", "设置", "授权", "弹幕配置", "中心")),
    ("APP",   2, ("APP", "app", "App")),
    ("网盘",   3, ("网盘", "夸克", "阿里", "UC", "115", "天翼", "百度", "迅雷", "PikPak",
                  "磁力", "BT", "种", "云盘", "盘搜", "分享")),
    ("直播",   4, ("直播", "体育", "球", "电视", "IPTV", "频道", "央视", "卫视")),
    ("短剧",   5, ("短剧", "竖屏", "小剧场")),
    ("听书",   6, ("听书", "音乐", "音频", "电台", "广播", "相声", "评书", "戏曲", "MV")),
]
DEFAULT_GROUP = (1, "影视")


def group_of(site):
    name = str(site.get("name") or "")
    api = str(site.get("api") or "")
    for label, idx, kws in GROUPS:
        for kw in kws:
            if kw in name:
                return idx, label
    if api.startswith("csp_") and any(k in api for k in ("App", "Ys", "Fox", "Gulu", "Hxq")):
        return 2, "APP"
    return DEFAULT_GROUP


kept.sort(key=lambda s: group_of(s)[0])   # Python sort 稳定，同组内保持原顺序
gstat = Counter(group_of(s)[1] for s in kept)
order = ["工具箱", "影视", "APP", "网盘", "直播", "短剧", "听书"]
print("站点分组：" + "  ".join(f"{g}={gstat[g]}" for g in order if gstat[g]))

# ── 6. 组装（顶层数组统一去重，国内 DoH 前置）─────────────────────────────
def dedup(items, keyfn):
    """保持原顺序去重，返回 (结果, 去掉的条数)"""
    seen, out_ = set(), []
    for it in items:
        k = keyfn(it)
        if k in seen:
            continue
        seen.add(k)
        out_.append(it)
    return out_, len(items) - len(out_)


def as_text(x):
    return (x if isinstance(x, str) else json.dumps(x, ensure_ascii=False,
                                                    sort_keys=True)).strip().lower()


# 国内解析器放最前：原始配置里只有 Google / Cloudflare / Quad9 等境外 DoH，
# 在国内基本连不上，DNS 解析处处超时，客户端表现为「点开一直转圈」。
DOMESTIC_DOH = [
    {"name": "AliDNS", "url": "https://dns.alidns.com/dns-query", "ips": ["223.5.5.5", "223.6.6.6"]},
    {"name": "DNSPod", "url": "https://doh.pub/dns-query", "ips": ["119.29.29.29", "1.12.12.12"]},
    {"name": "360",    "url": "https://doh.360.cn/dns-query",  "ips": ["101.226.4.6", "101.226.4.9"]},
]

out = OrderedDict()
out["spider"] = SPIDER
out["wallpaper"] = base.get("wallpaper", "")
out["danmaku"] = base.get("danmaku", "")
out["sites"] = kept
out["lives"] = lives
out["parses"] = parses

_skeleton = {}
for k in ("hosts", "flags", "doh", "rules", "ads"):
    v = base.get(k)
    if not v:
        continue
    if k == "doh":
        v = DOMESTIC_DOH + [x for x in v if isinstance(x, dict)
                            and "alidns" not in str(x.get("url")) and "doh.pub" not in str(x.get("url"))]
    keyfn = {
        "hosts": lambda x: str(x).strip().lower(),
        "flags": lambda x: str(x).strip().lower(),
        "doh":   lambda x: str(x.get("url") if isinstance(x, dict) else x).strip().lower(),
        "rules": lambda x: str(x.get("name") if isinstance(x, dict) else x).strip(),
        "ads":   as_text,
    }[k]
    v2, cut = dedup(v, keyfn)
    if cut:
        print(f"  {k:<6} 去重 −{cut}（{len(v)} → {len(v2)}）")
    out[k] = v2
    _skeleton[k] = len(v2)

# ── 7. 序列化：顶层键换行，每个站点一行，便于 diff 与人工核对 ─────────────
def dump(obj, path):
    L = ["{"]
    items = list(obj.items())
    for idx, (k, v) in enumerate(items):
        tail = "," if idx < len(items) - 1 else ""
        if isinstance(v, list) and v and isinstance(v[0], (dict, list)):
            L.append(f'  "{k}": [')
            for j, it in enumerate(v):
                t2 = "," if j < len(v) - 1 else ""
                L.append("    " + json.dumps(it, ensure_ascii=False,
                                             separators=(",", ":")) + t2)
            L.append("  ]" + tail)
        else:
            L.append(f'  "{k}": ' + json.dumps(v, ensure_ascii=False,
                                               separators=(",", ":")) + tail)
    L.append("}")
    text = "\n".join(L) + "\n"
    open(path, "w", encoding="utf-8", newline="\n").write(text)
    return len(text.encode("utf-8"))


size = dump(out, os.path.join(ROOT, "tvbox.json"))
print(f"\n已生成 tvbox.json  {size/1024:.1f} KB")

# ── 7.2 wmz 完整体 ────────────────────────────────────────────────────────
# 主配置受限于单一 spider，只能收 wmz 里 csp_ 兼容的 79 站。
# 它还有 16 个站（AList / Pan115 / WebDAV / Libvio / HDmoli / 4K 网盘几组）
# 用的是 261109.jar 独有的类，spider.jar 里根本没有，只能单独成一份、
# 用 wmz 自己的 jar 才跑得起来。
if WMZ:
    wmz_sites = [dict(s) for s in (WMZ.get("sites") or [])
                 if isinstance(s, dict) and s.get("name") and s.get("api")]
    # wmz 原版里「🐧咕噜丨蓝光秒播」出现了两次（jar 内置一份、远程 JS 一份），
    # 客户端会显示成两行同名条目，加后缀区分。key 保持唯一即可。
    seen_nm = Counter()
    for s in wmz_sites:
        seen_nm[s["name"]] += 1
        if seen_nm[s["name"]] > 1:
            idx = seen_nm[s["name"]]
            suffix = "·JS" if not str(s.get("api") or "").startswith("csp_") else f"·{idx}"
            s["name"] = s["name"] + suffix
            s["key"] = f'{s["key"]}_{idx}'
    wmz_sites.sort(key=lambda s: group_of(s)[0])

    w = OrderedDict()
    # 把 wmz 的 jar 收到本地，避免运行时依赖 gitcode 的可达性。
    # md5 必须与实际文件一致，否则 TVBox 会拒绝加载。
    import hashlib
    wmz_jar = os.path.join(ROOT, "jar", "wmz.jar")
    if os.path.exists(wmz_jar):
        h = hashlib.md5(open(wmz_jar, "rb").read()).hexdigest()
        w["spider"] = f"./jar/wmz.jar;md5;{h}"
    else:
        w["spider"] = WMZ["spider"]
    for k in ("wallpaper", "logo", "warningText", "lives", "parses",
              "flags", "rules", "doh", "ads", "ijk"):
        if WMZ.get(k):
            w[k] = WMZ[k]
    w["sites"] = wmz_sites
    n = dump(w, os.path.join(ROOT, "tvbox-wmz.json"))
    print(f"已生成 tvbox-wmz.json  {n/1024:.1f} KB  {len(wmz_sites)} 站（jar/wmz.jar）")

# ── 7.5 多仓入口 repo.json ────────────────────────────────────────────────
# TVBox / OK影视 的「多仓」格式：客户端先展示仓库列表，用户选一个进入。
RAW = "https://raw.githubusercontent.com/xiaolei7172/tvbox/master"
repo = {
    "urls": [
        {"name": f"🚀 全量合并 · {len(kept)} 站（推荐）", "url": f"{RAW}/tvbox.json"},
    ]
}
if WMZ:
    repo["urls"].append(
        {"name": f"🎬 wmz 原版 · {len(WMZ.get('sites') or [])} 站（含 AList/115/4K网盘）",
         "url": f"{RAW}/tvbox-wmz.json"})
repo["urls"] += [
    {"name": "📺 家庭电视 · jsm（精简，158 站）", "url": f"{RAW}/jsm.json"},
    {"name": "📱 综合线路 · dianshi（159 站 + 29 解析）", "url": f"{RAW}/dianshi.json"},
    {"name": "🧩 JS 规则库 · js（298 站，drpy2 全量）", "url": f"{RAW}/js.json"},
    {"name": "🎯 大而全 · 0821（多直播线路）", "url": f"{RAW}/0821.json"},
    {"name": "⚡ 极简 · 0827（33 站，启动快）", "url": f"{RAW}/0827.json"},
    {"name": "☁️ 网盘专精 · 0825（135 站）", "url": f"{RAW}/0825.json"},
    {"name": "🍚 饭太硬 · fty", "url": f"{RAW}/fty.json"},
    {"name": "🌊 潇洒 · xiaosa", "url": f"{RAW}/xiaosa/api.json"},
    {"name": "💮 香雅情 · XYQ", "url": f"{RAW}/XYQ.json"},
]
repo_path = os.path.join(ROOT, "repo.json")
open(repo_path, "w", encoding="utf-8", newline="\n").write(
    json.dumps(repo, ensure_ascii=False, indent=2) + "\n")
print(f"已生成 repo.json   {len(repo['urls'])} 个仓库入口")

# ── 7.6 国内加速版多仓 repo-cn.json ───────────────────────────────────────
# 国内直连 raw.githubusercontent.com 基本不通，多仓里的每个子地址都会失败。
# 这里把子地址统一套上加速前缀；配置内部的相对路径（./js/…）会挂到同一个
# 前缀后面，代理按路径透传，所以依然能取到文件。
ACCEL = "https://gh-proxy.com/"
repo_cn = {"urls": [dict(x, url=ACCEL + x["url"]) for x in repo["urls"]]}
open(os.path.join(ROOT, "repo-cn.json"), "w", encoding="utf-8", newline="\n").write(
    json.dumps(repo_cn, ensure_ascii=False, indent=2) + "\n")
print(f"已生成 repo-cn.json  加速前缀 {ACCEL}")

# ── 8. 统计输出 ───────────────────────────────────────────────────────────
print("\n站点来源统计：")
for k, v in sorted(stat.items(), key=lambda x: -x[1]):
    print(f"  {k:<34}{v:>4}")

kinds = Counter()
for s in kept:
    api = str(s.get("api") or "")
    if api.startswith("csp_"):
        kinds["jar 内置(csp_)"] += 1
    elif "drpy" in api or api.endswith(".js"):
        kinds["JS 源"] += 1
    elif api.endswith(".py"):
        kinds["Python 源"] += 1
    elif re.match(r"https?://", api):
        kinds["直连 API"] += 1
    else:
        kinds["其他"] += 1
print("\n最终构成：")
for k, v in kinds.most_common():
    print(f"  {k:<18}{v:>4}")

if dropped:
    print("\n因 ext 断链被剔除的站点：")
    for src, nm, ext in dropped:
        print(f"  [{src}] {nm}  ->  {ext}")

# ── 9. 校验 ───────────────────────────────────────────────────────────────
chk = json.load(open(os.path.join(ROOT, "tvbox.json"), encoding="utf-8"))
dup_key = [k for k, v in Counter(s["key"] for s in chk["sites"]).items() if v > 1]
dup_name = [k for k, v in Counter(s["name"] for s in chk["sites"]).items() if v > 1]
print(f"\n校验：严格 JSON ✅  key 重复 {len(dup_key)}  name 重复 {len(dup_name)}")
