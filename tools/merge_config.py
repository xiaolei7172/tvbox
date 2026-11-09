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


kept, dropped = [], []
keys, names = set(), set()
stat = Counter()


def add_sites(src_name, sites, allow_csp=False, forbid_csp=False):
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
        if nm in names:
            stat[f"{src_name}:name重复"] += 1
            continue
        if ext_broken(s):
            stat[f"{src_name}:ext断链"] += 1
            dropped.append((src_name, nm, s.get("ext")))
            continue
        keys.add(k)
        names.add(nm)
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

print(f"\n站点合计 {len(kept)}，剔除 {sum(v for k, v in stat.items() if '收录' not in k)}")

# ── 4. 合并 lives（URL 规范化去重）────────────────────────────────────────
def norm_url(u):
    """用于判重的规范化：去协议差异、去尾部斜杠、统一小写主机"""
    s = str(u or "").strip()
    s = re.sub(r"^https?://", "//", s, flags=re.I)
    s = s.rstrip("/")
    return s.lower()


lives, seen_live = [], set()
for f in SAME_JAR + EXTRA:
    d = load(f)
    if not d:
        continue
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
        seen_live.add(n)
        lives.append(lv)

# ── 5. 合并 parses（清洗无效项）──────────────────────────────────────────
parses, seen_parse = [], set()
for f in SAME_JAR + EXTRA:
    d = load(f)
    if not d:
        continue
    for ps in d.get("parses") or []:
        if not isinstance(ps, dict):
            continue
        u = str(ps.get("url") or "").strip()
        if not u or u.lower() in {"demo", "null", "none"}:
            continue
        sig = (ps.get("name"), norm_url(u), ps.get("type"))
        if sig in seen_parse:
            continue
        seen_parse.add(sig)
        parses.append(ps)

print(f"直播源 {len(lives)} 个，解析 {len(parses)} 个")

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

# ── 6. 组装 ───────────────────────────────────────────────────────────────
out = OrderedDict()
out["spider"] = SPIDER
out["wallpaper"] = base.get("wallpaper", "")
out["danmaku"] = base.get("danmaku", "")
out["sites"] = kept
out["lives"] = lives
out["parses"] = parses
for k in ("hosts", "flags", "doh", "rules", "ads"):
    if base.get(k):
        out[k] = base[k]

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

# ── 7.5 多仓入口 repo.json ────────────────────────────────────────────────
# TVBox / OK影视 的「多仓」格式：客户端先展示仓库列表，用户选一个进入。
RAW = "https://raw.githubusercontent.com/xiaolei7172/tvbox/master"
repo = {
    "urls": [
        {"name": f"🚀 全量合并 · {len(kept)} 站（推荐）", "url": f"{RAW}/tvbox.json"},
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
}
repo_path = os.path.join(ROOT, "repo.json")
open(repo_path, "w", encoding="utf-8", newline="\n").write(
    json.dumps(repo, ensure_ascii=False, indent=2) + "\n")
print(f"已生成 repo.json   {len(repo['urls'])} 个仓库入口")

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
