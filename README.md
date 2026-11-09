# TvBox / OK影视 配置仓库

OK影视、TVBox、猫影视配置文件集合。所有资源均来自各路大神无私分享。

> 本仓库为 [`qist/tvbox`](https://github.com/qist/tvbox) 的镜像分支，用于个人自用与配置归档。
> 上游原始说明（APP 推荐、网盘授权、各路大佬配置地址）已完整保留在 [docs/上游说明存档.md](docs/上游说明存档.md)。

---

## 快速开始

在 OK影视 / TVBox 的「配置地址」中填入以下任一地址（`<user>` 替换为 `xiaolei7172`）：

| 需求 | 配置地址 | 点播源 | 直播 | 说明 |
|---|---|---:|---:|---|
| **⭐ 一站式（推荐）** | `https://raw.githubusercontent.com/<user>/tvbox/master/tvbox.json` | **436** | 14 | 全仓合并版，已剔除死链与重复源 |
| wmz 原版 | `https://raw.githubusercontent.com/<user>/tvbox/master/tvbox-wmz.json` | 95 | 2 | 补齐主配置收不了的 16 个 jar 专属站（AList / 115 / 4K 网盘） |
| 多仓入口 | `https://raw.githubusercontent.com/<user>/tvbox/master/repo.json` | — | — | 客户端显示仓库列表，自行切换 |
| 电视首选 | `https://raw.githubusercontent.com/<user>/tvbox/master/jsm.json` | 158 | 3 | 家庭电视适用，已删 YouTube 直播 |
| 手机 / 综合 | `https://raw.githubusercontent.com/<user>/tvbox/master/dianshi.json` | 159 | 1 | 电视端 + 自定义 app_sites |
| 大而全 | `https://raw.githubusercontent.com/<user>/tvbox/master/0821.json` | 86 | 16 | 饭太硬底包 + 多直播线路 |
| 极简 | `https://raw.githubusercontent.com/<user>/tvbox/master/0827.json` | 33 | 0 | 仅 fongmi jar，启动快 |
| JS 规则为主 | `https://raw.githubusercontent.com/<user>/tvbox/master/js.json` | 296 | 2 | drpy2 全量 JS 源 |
| 潇洒接口 | `https://raw.githubusercontent.com/<user>/tvbox/master/xiaosa/api.json` | 112 | 1 | 上游自动更新 |

### `tvbox.json` 是什么

由仓库内 13 个配置 + 外部源 wmz 合并而成，可直接单地址接入：

| 项目 | 数值 |
|---|---|
| 站点总数 | 436（key/name 双重去重 + 死链/重复源黑名单，零重复） |
| 构成 | JS 源 246 · jar 内置 194 · 直连 API 52 · Python 源 14 |
| 直播源 | 14 个（URL 规范化去重） |
| 解析 | 48 个 |
| spider | `./jar/spider.jar`（1.85 MB，172 个内置类） |
| 体积 | 112 KB |

列表按「工具箱 → 影视 → APP → 网盘 → 直播 → 短剧 → 听书」顺序排列，打开即有序。

内置 **555电影** 专项规则（`js/555电影.js`）：域名从发布页 `data-info` 自动解析，换域名不用改配置；前 12 集直连 m3u8 秒开，长剧其余集交给嗅探。

合并取舍与重新生成方法见 [docs/合并说明.md](docs/合并说明.md)。

**GitHub 访问慢**时，在地址前加代理前缀（任选一个）：

```
https://gh-proxy.net/
https://github.moeyy.xyz/
https://gh-proxy.com/
https://ghproxy.net/
```

例：`https://gh-proxy.net/https://raw.githubusercontent.com/xiaolei7172/tvbox/master/tvbox.json`

---

## 仓库地图

```
.
├── tvbox.json             ⭐ 全量合并配置（436 站，推荐单地址接入）
├── tvbox-wmz.json         wmz 原版配置（95 站，配 jar/wmz.jar）
├── repo.json              多仓入口（客户端显示仓库列表）
├── *.json                 其余独立配置（保留原有订阅地址，勿移动/改名）
├── *.m3u / *.txt          直播源（见下表）
├── jar/                   spider 包（fan.txt 实为 jar，仅改扩展名绕 MIME 检查）
├── js/                    drpy2 JS 规则
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
| `tools/check_health.py` | 9 项自检，退出码可接 CI |
| `tools/tvbox.py` / `xiao.py` / `fty.py` / `build_local.py` | Actions 每日自动更新用 |

### 直播源

| 文件 | 频道数 | 体积 | 类型 |
|---|---:|---:|---|
| `list.m3u` | 824 | 88 KB | m3u，轻量 |
| `listx.m3u` | 25,821 | 6.1 MB | m3u，全量（低配盒子慎用） |
| `livex.m3u` | 14,651 | 1.0 MB | m3u |
| `radio.m3u` | 1,478 | 160 KB | 电台 |
| `tvboxtv.txt` | — | 152 KB | TVBox type-0（默认直播源） |
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
