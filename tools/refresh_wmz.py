# -*- coding: utf-8 -*-
"""
刷新 wmz 外部源快照。

wmz 的订阅地址返回的不是明文 JSON，而是「YmFzZTY0**」前缀 + 整段 base64。
它的 spider 指向 gitcode 上一个带日期的 jar（261109.jar），所以配置和 jar
是配套升级的 —— 只换配置不换 jar 会加载失败，反之亦然。

本脚本做两件事，任何一步失败都保留原有文件不动，绝不让仓库进入半更新状态：
  1. 拉 sources/wmz.txt
  2. 从配置里取出 spider URL，下载对应 jar 到 jar/wmz.jar，并按声明的 MD5 校验

用法：
    python tools/refresh_wmz.py          # 刷新
    python tools/refresh_wmz.py --check  # 只检查远端是否有更新，不写文件
"""
import base64
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_URL = "https://8815.kstore.vip/tvbox/wmz"
MARKER = "YmFzZTY0**"
TXT = os.path.join(ROOT, "sources", "wmz.txt")
JAR = os.path.join(ROOT, "jar", "wmz.jar")
UA = ("Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")

sys.stdout.reconfigure(encoding="utf-8")


def fetch(url, timeout=60):
    # gitcode 等图床对裸 url 里的中文/空格敏感，统一 quote 一次
    safe = urllib.parse.quote(url, safe=":/?&=%;,+#[]@!$'()*~")
    req = urllib.request.Request(safe, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def decode(raw_text):
    t = raw_text.strip()
    body = t[len(MARKER):] if t.startswith(MARKER) else t
    if not re.fullmatch(r"[A-Za-z0-9+/=\s]+", body):
        raise ValueError("载荷不是合法 base64")
    body = re.sub(r"\s+", "", body)
    body += "=" * (-len(body) % 4)
    return json.loads(base64.b64decode(body).decode("utf-8"))


def main():
    check_only = "--check" in sys.argv
    print(f"拉取 {SRC_URL}")
    try:
        raw = fetch(SRC_URL).decode("utf-8", "ignore")
    except Exception as e:
        print(f"[!] 拉取失败，保留现有快照：{e}")
        return 1

    if not raw.strip():
        print("[!] 返回空内容，保留现有快照")
        return 1

    try:
        cfg = decode(raw)
        sites = cfg.get("sites") or []
        if not sites:
            raise ValueError("sites 为空")
    except Exception as e:
        print(f"[!] 解码失败（源格式可能变了），保留现有快照：{e}")
        return 1

    print(f"    站点 {len(sites)}  直播 {len(cfg.get('lives') or [])}  "
          f"解析 {len(cfg.get('parses') or [])}")

    spider = str(cfg.get("spider") or "")
    m = re.search(r"md5;([0-9a-fA-F]{32})", spider)
    want_md5 = m.group(1).lower() if m else ""
    jar_url = spider.split(";md5;")[0].strip()
    print(f"    spider jar: {jar_url}")
    print(f"    声明 MD5  : {want_md5 or '(未声明)'}")

    old_md5 = ""
    if os.path.exists(JAR):
        old_md5 = hashlib.md5(open(JAR, "rb").read()).hexdigest()
    print(f"    本地 MD5  : {old_md5 or '(无)'}")

    if check_only:
        print("    jar 需更新" if old_md5 != want_md5 else "    jar 已最新")
        return 0

    changed = False

    # 1) 配置文件
    old_txt = open(TXT, encoding="utf-8").read() if os.path.exists(TXT) else ""
    if raw.strip() != old_txt.strip():
        os.makedirs(os.path.dirname(TXT), exist_ok=True)
        open(TXT, "w", encoding="utf-8", newline="\n").write(raw.rstrip() + "\n")
        print("    [写入] sources/wmz.txt")
        changed = True
    else:
        print("    配置无变化")

    # 2) 配套 jar
    if want_md5 and old_md5 != want_md5:
        try:
            blob = fetch(jar_url, timeout=180)
            got = hashlib.md5(blob).hexdigest()
            if got != want_md5:
                print(f"[!] jar MD5 不符（声明 {want_md5} / 实际 {got}），不写入")
                return 1
            os.makedirs(os.path.dirname(JAR), exist_ok=True)
            open(JAR, "wb").write(blob)
            print(f"    [写入] jar/wmz.jar  {len(blob)/1048576:.2f} MB  md5={got}")
            changed = True
        except Exception as e:
            print(f"[!] jar 下载失败，保留原 jar：{e}")
            return 1

    print("完成：有更新" if changed else "完成：无变化")
    return 0


if __name__ == "__main__":
    sys.exit(main())
