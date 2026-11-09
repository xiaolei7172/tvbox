# TvBox / OK影视 配置仓库

OK影视、TVBox、猫影视配置文件集合。所有资源均来自各路大神无私分享。

> 本仓库为 [`qist/tvbox`](https://github.com/qist/tvbox) 的镜像分支，用于个人自用与配置归档。
> 上游原始说明（APP 推荐、网盘授权、各路大佬配置地址）已完整保留在 [docs/上游说明存档.md](docs/上游说明存档.md)。

---

## 快速开始

国内直连 `raw.githubusercontent.com` 基本不通 —— 本机实测 3 次全部超时。下面的地址都带了加速前缀，**复制即用**。

排序依据：2026-11-09 对 29 个候选逐个真实拉取 `tvbox.json`（97,947 B），每个 **5 次取中位数**，
并校验返回内容必须是合法 JSON 且站数为 434 —— 把跳转页、验证页、截断响应都判为失败。

### 🏅 按速度排序（实测最快在前）

测法：9 个候选**交错轮询 7 轮**（每轮把全部镜像打一遍，消除时间偏差），取下单次耗时中位数。
单轮"先测谁后测谁"会带来 10 倍误差 —— 同一镜像先测 0.39 s、后测 3.71 s，所以必须交错。

| # | 镜像 | 中位 | 波动范围 | 配套配置 | 取 jar | 标签 |
|---|---|---|---:|---|---|---|
| 1 | `https://cdn.jsdmirror.com/gh/xiaolei7172/tvbox@master/` | **0.35 s** | 0.18–2.07 | cdn 版 | ❌ | **优质** |
| 2 | `https://jsd.onmicrosoft.cn/gh/xiaolei7172/tvbox@master/` | **0.53 s** | 0.17–0.65 | cdn 版 | ❌ | **优质** · 最稳 |
| 3 | `https://fastly.jsdelivr.net/gh/xiaolei7172/tvbox@master/` | **0.57 s** | 0.48–0.76 | cdn 版 | ❌ | **优质** |
| 4 | `https://jsdelivr.b-cdn.net/gh/xiaolei7172/tvbox@master/` | 1.37 s | 1.24–1.42 | cdn 版 | ❌ | **优质** |
| 5 | `https://ghproxy.net/` | 1.76 s | 1.60–1.83 | 普通版 | ✅ | **优质** · **全仓可直取** |
| 6 | `https://testingcf.jsdelivr.net/gh/xiaolei7172/tvbox@master/` | 1.83 s | 1.46–3.66 | cdn 版 | ❌ | 备用 |
| 7 | `https://gcore.jsdelivr.net/gh/xiaolei7172/tvbox@master/` | 2.14 s | 1.07–5.20 | cdn 版 | ❌ | 备用 |
| 8 | `https://ghfile.geekertao.top/` | 2.49 s | 1.54–5.36 | 普通版 | ⚠️ | **不推荐**，大文件会截断 |
| 9 | `https://gh-proxy.com/` | 3.54 s | 1.50–6.13 | 普通版 | ✅ | 兜底 · 7 轮中 1 次失败 |

**只想粘一个地址、不想管两套配置 → 用第 5 条**，它是"配置和 jar 走同一个源"里最快的一条。
前缀式的完整地址 = 前缀 + 原始地址，例如：

```
https://ghproxy.net/https://raw.githubusercontent.com/xiaolei7172/tvbox/master/tvbox.json
```

jsDelivr 式是**整段改写**，别拼错（`/gh/用户/仓库@分支/路径`）：

```
https://cdn.jsdmirror.com/gh/xiaolei7172/tvbox@master/tvbox-cdn.json
```

> `ghfile.geekertao.top` 单独点名：配置拉取 2.49 s 看着不错，但第二次取 `spider.jar` 时
> **只返回了 1,343,488 B（应为 1,937,684 B）**，即传输被截断。jar 有 md5 校验，截断的包客户端直接拒绝加载，
> 表现就是"配置能进、点开全报错"。这类镜像不能用。


### ⚠️ 用 CDN 地址必须配 `tvbox-cdn.json`

`tvbox.json` 和 `tvbox-cdn.json` **只差一个字段**，不能混用：

| 配置 | spider 写法 | 适用于 |
|---|---|---|
| `tvbox.json` | `./jar/spider.jar;md5;…`（相对路径） | gh-proxy 这类**全路径透传**的代理 |
| `tvbox-cdn.json` | `https://gh-proxy.com/https://raw.githubusercontent.com/…/jar/spider.jar;md5;…`（绝对地址） | jsDelivr 这类 **CDN** |

原因是实测出来的一个硬限制：**jsDelivr 系镜像会按扩展名把 `.jar` 拦成 `403 Forbidden`**。

| 同一镜像取不同文件 | 结果 |
|---|---|
| `…/jar/spider.jar`（1.85 MB） | ❌ `403 Forbidden`，响应体只有 9 字节 |
| `…/jar/fan.txt`（1.38 MB，实际也是个 jar 改名） | ✅ 200，1,411,181 B |
| `…/js/555电影.js` | ✅ 200，7,435 B |

体积不是原因，**扩展名才是**。所以配置放在 CDN 上时，相对路径的 `./jar/spider.jar` 会跟着 403，
**194 个 jar 内置源（`csp_*`）全部失效**。`tvbox-cdn.json` 把 spider 换成绝对地址走 gh-proxy，
其余字段与 `tvbox.json` 逐字节一致，由合并脚本自动生成，不会脱节。

代价：jsDelivr 有 **12 小时左右缓存**，每日更新会滞后；要跟得最新就用第 5 条的 `gh-proxy.com`。

### 全部配置地址（统一用 gh-proxy.com）

| 配置 | 内容 | 国内加速地址 | 原始地址 |
|---|---|---|---|
| **⭐ 全量合并（推荐）** | **434** 站 · 13 直播 · 38 解析 | `https://gh-proxy.com/https://raw.githubusercontent.com/xiaolei7172/tvbox/master/tvbox.json` | [raw](https://raw.githubusercontent.com/xiaolei7172/tvbox/master/tvbox.json) |
| CDN 专用版 | 与上表同内容，spider 走绝对地址 | 见上方第 1–4、6–7 条（jsDelivr 前缀） | [raw](https://raw.githubusercontent.com/xiaolei7172/tvbox/master/tvbox-cdn.json) |
| wmz 原版 | 95 站，补齐 16 个 jar 专属站（AList / 115 / 4K 网盘） | `https://gh-proxy.com/https://raw.githubusercontent.com/xiaolei7172/tvbox/master/tvbox-wmz.json` | [raw](https://raw.githubusercontent.com/xiaolei7172/tvbox/master/tvbox-wmz.json) |
| 多仓入口（加速版） | 11 个仓库，子地址已套加速前缀 | `https://gh-proxy.com/https://raw.githubusercontent.com/xiaolei7172/tvbox/master/repo-cn.json` | [raw](https://raw.githubusercontent.com/xiaolei7172/tvbox/master/repo.json) |
| 电视首选 | jsm，158 站，已删 YouTube 直播 | `https://gh-proxy.com/https://raw.githubusercontent.com/xiaolei7172/tvbox/master/jsm.json` | [raw](https://raw.githubusercontent.com/xiaolei7172/tvbox/master/jsm.json) |
| 手机 / 综合 | dianshi，159 站 + 29 解析 | `https://gh-proxy.com/https://raw.githubusercontent.com/xiaolei7172/tvbox/master/dianshi.json` | [raw](https://raw.githubusercontent.com/xiaolei7172/tvbox/master/dianshi.json) |
| 极简 | 0827，33 站，低配盒子启动快 | `https://gh-proxy.com/https://raw.githubusercontent.com/xiaolei7172/tvbox/master/0827.json` | [raw](https://raw.githubusercontent.com/xiaolei7172/tvbox/master/0827.json) |
| JS 规则为主 | js.json，296 站 drpy2 全量 | `https://gh-proxy.com/https://raw.githubusercontent.com/xiaolei7172/tvbox/master/js.json` | [raw](https://raw.githubusercontent.com/xiaolei7172/tvbox/master/js.json) |

> 前缀式加速是**直接拼接**：`https://gh-proxy.com/` + `https://raw.githubusercontent.com/...`。
> 配置里所有 `./js/xxx.js`、`./jar/spider.jar` 这类相对路径也会跟着走同一个前缀，代理按路径透传，取文件正常。
>
> jsDelivr 式是**整段改写**，别拼错：
> `https://gcore.jsdelivr.net/gh/xiaolei7172/tvbox@master/tvbox.json`（注意是 `/gh/用户/仓库@分支/路径`，且必须配 cdn 版）。

### ❌ 实测不通的候选（别用）

| 镜像 | 现象 |
|---|---|
| `raw.githubusercontent.com` 直连 | 3 次全超时（解析到的 IP 被掐） |
| `gh-proxy.net` | 域名被劫持，返回 546 B 的 `window.location.replace(…?js=<JWT>)` 跳转页 |
| `github.moeyy.xyz` | 域名已注销（NXDOMAIN），父域 NS 还在 |
| `ghps.cc` | 返回注入的 `<script>` 页面，不是文件 |
| `ghproxy.cc` · `cf.ghproxy.cc` | 301 跳转后拿不到文件 |
| `ghproxy.1888866.xyz` · `ghp.arslantu.xyz` | HTTP 525（源站 TLS 握手失败） |
| `ghproxy.homeboyc.cn` | HTTP 403 |
| `ghfast.top` · `gh.llkk.cc` · `gh.xxooo.cf` · `hub.gitmirror.com` · `gh.jasonzeng.dev` · `gh-proxy.top` · `gh.7c7.cc` · `ghproxy.cfd` · `cdn.jsdelivr.net` · `cdn.statically.io` · `raw.githack.com` | 连接超时 / 无响应 |

复跑测速：`python tools/bench_mirrors.py`（生成 `bench-result.json`）。

**都不行就自建**：仓库里带了一份 Cloudflare Worker 代理脚本 `tools/cf-proxy-worker.js`，
粘到 Workers 里部署，绑自己域名，然后把它当前缀用（免费额度够个人用，不怕公共加速站失效）。

### `tvbox.json` 是什么

由仓库内 13 个配置 + 外部源 wmz 合并而成，可直接单地址接入：

| 项目 | 数值 |
|---|---|
| 站点总数 | 434（key/name 双重去重 + 死链黑名单 + 规则同源合并，零重复） |
| 构成 | JS 源 203 · jar 内置 174 · 直连 API 44 · Python 源 13 |
| 直播源 | 13 个（URL 规范化 + 同格式列表重合度去重） |
| 解析 | 38 个（同接口只留一条） |
| 广告过滤 | 60 条（原 118 条，去重 58） |
| DNS | 前 3 个是阿里 / DNSPod / 360 国内 DoH，境外解析器降为兜底 |
| spider | `./jar/spider.jar`（1.85 MB，172 个内置类） |
| 体积 | 96 KB |

列表按「工具箱 → 影视 → APP → 网盘 → 直播 → 短剧 → 听书」顺序排列，打开即有序。

内置 **555电影** 专项规则（`js/555电影.js`）：域名从发布页 `data-info` 自动解析，换域名不用改配置；前 12 集直连 m3u8 秒开，长剧其余集交给嗅探。

合并取舍与重新生成方法见 [docs/合并说明.md](docs/合并说明.md)，死链与重复源的判定过程见 [docs/源体检报告.md](docs/源体检报告.md)。

### 本版做的优化（2026-11-09）

| # | 项 | 之前 → 之后 |
|---|---|---|
| 1 | 广告过滤规则去重 | 118 → **60** 条（同名重复占一半，白占启动时间） |
| 2 | 解析接口去重 | 48 → **38** 个（「虾米 / -虾米-」「云解析 / 淘片」是同一个 url 挂三个名字） |
| 3 | 直播源去重 | 14 → **13** 个（`tvboxtv.txt` 与 `tvlive.txt` 频道重合 99.7%）；两个同名「初秋语」改为 `•M3U` / `•TXT` 区分 |
| 4 | DNS 解析器 | 原本只有 Google / Cloudflare / Quad9 等境外 DoH，国内处处超时 → 前置阿里 / DNSPod / 360 |
| 5 | 失效加速站本地化 | `gh-proxy.net`（已被劫持）、`github.moeyy.xyz`（已注销）上的 7 个站点，引擎与规则全部改指向仓库自带的 `./lib` + 本地规则 |
| 6 | 规则同源合并 | 本地化后有 2 个站点与已有条目完全同源，合并掉（436 → **434**） |

---

## 仓库地图

```
.
├── tvbox.json             ⭐ 全量合并配置（434 站，推荐单地址接入）
├── tvbox-cdn.json         CDN 专用版（spider 走绝对地址，配 jsDelivr 系用）
├── repo-cn.json           多仓入口·加速版（子地址已套 gh-proxy.com，国内可直接用）
├── bench-result.json      镜像测速结果（tools/bench_mirrors.py 生成）
├── tvbox-wmz.json         wmz 原版配置（95 站，配 jar/wmz.jar）
├── repo.json              多仓入口（客户端显示仓库列表）
├── *.json                 其余独立配置（保留原有订阅地址，勿移动/改名）
├── *.m3u / *.txt          直播源（见下表）
├── jar/                   spider 包（fan.txt 实为 jar，仅改扩展名绕 MIME 检查）
├── js/                    drpy2 JS 规则（js/ext/ 放上游加密规则的明文版）
├── lib/                   解析引擎 + 代理内核 + token.json（密钥配置）
├── json/                  站点规则集（网盘 / 磁力 / 各类 API）
├── py/                    PY 源（TVBox Python 支持）
├── FTY/                   饭太硬 EXT 扩展
├── XBPQ/                  小米小爆脾气源
├── XYQHiker/              香雅情 Hiker 规则
├── XYQBiu/                香雅情 BIU 规则
├── biliext/               B 站扩展（含课堂、少儿教育）
├── cat/                   猫影视 CatVodOpen 整套规则 + dist 构建产物
├── xiaosa/                潇洒接口完整镜像（有独立对外 URL）
├── live/                  省级运营商 IPTV 源
├── sources/               外部源快照（wmz.txt，base64 原样存放）
├── tools/                 ★ 自动更新流水线 · 配置合并 · 自检
├── archive/               已停用资源归档
└── docs/                  文档
```

### 工具

| 脚本 | 作用 |
|---|---|
| `tools/merge_config.py` | 13 配置 + wmz → `tvbox.json` + `tvbox-wmz.json` + `repo.json` |
| `tools/refresh_wmz.py` | 刷新 wmz 配置快照与配套 jar（`--check` 只检查不写） |
| `tools/bench_mirrors.py` | 29 个加速镜像实测排序，校验内容后输出 `bench-result.json` |
| `tools/check_health.py` | 9 项自检，退出码可接 CI |
| `tools/tvbox.py` / `xiao.py` / `fty.py` / `build_local.py` | Actions 每日自动更新用 |

### 直播源

| 文件 | 频道数 | 体积 | 类型 |
|---|---:|---:|---|
| `list.m3u` | 824 | 88 KB | m3u，轻量 |
| `listx.m3u` | 25,821 | 6.1 MB | m3u，全量（低配盒子慎用） |
| `livex.m3u` | 14,651 | 1.0 MB | m3u |
| `radio.m3u` | 1,478 | 160 KB | 电台 |
| `tvboxtv.txt` | — | 152 KB | TVBox type-0，频道为 `tvlive.txt` 子集，配置里已不再单独挂载（`dianshi.json` 仍在用） |
| `tvlive.txt` / `zb.txt` | — | 156 / 232 KB | TVBox type-0 |

---

## 维护

### 自动更新

`.github/workflows/run.yml` 每日 05:20（UTC）执行完整流水线：

```
拉上游源 → 刷新 wmz 快照 → 重新合并配置 → 体检 → 提交推送
```

重写的文件：`dianshi.json` · `jsm.json` · `fty.json` · `jar/fan.txt` · `jar/spider.jar` · `FTY/` · `xiaosa/` · `sources/wmz.txt` · `jar/wmz.jar` · `tvbox.json` · `tvbox-wmz.json` · `repo.json`

`merge_config.py` 每次都会重新从 jar 的 dex 提取 `csp_` 白名单，所以上游换 jar 也不会让合并配置失效。任何一步失败都只跳过、不写入半成品。

**fork 后需手动启用**：`Settings → Actions → General → Allow all actions and reusable workflows`。
未启用时每日更新不会执行。

也可在 `Actions → Update xiaosa → Run workflow` 手动触发。

### 自检

```bash
python tools/check_health.py            # 人类可读报告
python tools/check_health.py --json     # JSON 输出
```

检查 9 项：JSON 合法性（区分 JSONC）、配置结构、本地引用断链、spider MD5 一致性、
重复文件、敏感凭证、文件名风险、Python 语法、体积分布。退出码非 0 表示存在 P0 问题，
可直接接入 CI。

### 已知状态

- 13 个本地 spider 的 MD5 声明与 jar 实际值 **全部一致**
- 本地引用断链 **0 处**（`lib/wogg.json`、`lib/wog.json` 已统一改指 `json/wogg.json`，
  `西门[V2]` 因上游从未提供规则文件已从配置移除）
- 在线源失效率约 35%（抽样 70 个高频 URL），属 TVBox 源常态

完整体检结论见 [docs/体检报告.md](docs/体检报告.md)。

---

## 免责声明

所有资源均来自于各路大神无私分享，如有侵权，请联系删除。

所有以任何方式查看本仓库内容的人、或直接或间接使用本仓库内容的使用者都应仔细阅读此声明。本仓库管理者保留随时更改或补充此免责声明的权利。一旦使用、复制、修改了本仓库内容，则视为您已接受此免责声明。

本仓库管理者不能保证本仓库内容的合法性、准确性、完整性和有效性，请根据情况自行判断。本仓库内容，仅用于测试和学习研究，禁止用于商业用途，不得将其用于违反国家、地区、组织等的法律法规或相关规定的其他用途，禁止任何公众号、自媒体进行任何形式的转载、发布，请不要在中华人民共和国境内使用本仓库内容，否则后果自负。

本仓库内容中涉及的第三方硬件、软件等，与本仓库内容没有任何直接或间接的关系。本仓库内容仅对部署和使用过程进行客观描述，不代表支持使用任何第三方硬件、软件。使用任何第三方硬件、软件，所造成的一切后果由使用的个人或组织承担，与本仓库内容无关。

所有直接或间接使用本仓库内容的个人和组织，应 24 小时内完成学习和研究，并及时删除本仓库内容。如对本仓库内容的功能有需求，应自行开发相关功能。所有基于本仓库内容的源代码，进行的任何修改，为其他个人或组织的自发行为，与本仓库内容没有任何直接或间接的关系，所造成的一切后果亦与本仓库内容和本仓库管理者无关。

---

## 致谢

上游：[qist/tvbox](https://github.com/qist/tvbox)（12.7k stars）

各路配置作者：饭太硬、okjack、王二小放牛娃、摸鱼儿、霜辉月明(py)、小米小爆脾气、南风、巧技、Ray、俊于、橘子柚、香雅情、潇洒、fongmi、唐三、Panda Groove、道长(drpy) 等（排名不分先后，完整清单见 [docs/上游说明存档.md](docs/上游说明存档.md)）。
