# archive · 已停用资源归档

本目录存放**已确认无引用、但不想直接删除**的资源。保留用于回溯，不参与任何配置加载。

## legacy-proxy/

| 文件 | 体积 | 停用原因 |
|---|---:|---|
| `aliproxy.gz` | 5.1 MB | `lib/token.json` 中 `"aliproxy_url": ""` 为空，功能未启用 |
| `aliproxy.32.gz` | 5.2 MB | 同上（32 位版本） |
| `aliproxy.md5` / `aliproxy.32.md5` | 34 B | 校验文件，随附 |

**恢复方式**：将文件移回 `lib/`，并在 `lib/token.json` 中填入有效的 `aliproxy_url`。

```bash
mv archive/legacy-proxy/aliproxy*.gz archive/legacy-proxy/aliproxy*.md5 lib/
```

> 归档收益：仓库工作区减少 10.3 MB。注意 `.git` 历史中仍保留这些文件的旧版本，
> 若需彻底瘦身须重写历史（`git filter-repo`），这会改变所有 commit SHA，非必要不做。
