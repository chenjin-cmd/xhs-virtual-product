# 怎么拿到对标材料

脚本来自 `xhs-account-teardown` 的思路，来源和 MIT 许可见 `../THIRD_PARTY_NOTICES.md`。它是可选功能：有截图或正文时，直接用这些材料也能拆。

## 怎么运行

在技能目录运行。真实结果放到仓库外：

```bash
python3 scripts/fetch_profile.py "https://www.xiaohongshu.com/user/profile/<user_id>" -o "$HOME/xhs-work/subject-a"
python3 scripts/fetch_note.py "https://www.xiaohongshu.com/explore/<note_id>?xsec_token=<token>&xsec_source=pc_user" -o "$HOME/xhs-work/subject-a/notes/note-a"
```

第一个命令可以用完整主页链接或 24 位 user_id。第二个命令必须是用户提供的、同一篇笔记的完整链接，里面要有 `xsec_token`。不要从主页 ID 猜笔记 ID，也不要用 A 笔记的 token 去抓 B 笔记。

`-o` 是必填的，而且不能放在这个仓库里。每个账号和每篇笔记用不同目录。token 不会写进 JSON 或报错信息，但也别把命令历史、Cookie 或 token 提交进 Git。

脚本默认每次请求间隔 1.5 秒，可以用 `--interval 2` 放慢一点。它不会自动重试。第一次图片下载失败后，后面的图片不再请求。同一个目录再次运行，会换掉这个命令之前生成的文件；重要结果请另存一个目录。

## 它能拿什么

| 材料 | 可能拿到 | 拿不到 |
|---|---|---|
| 主页 | 当前第一页、账号信息、封面 | 全部历史、搜索、评论、店铺销量、利润 |
| 同篇带 token 的笔记 | 正文、标签、互动、图片 | 评论、订单、店铺经营、完整视频 |
| 用户给的截图/文字 | 截图或文字里看得到的内容 | 截图外的平台内容 |

匿名主页通常只能看到很少一部分笔记。以前的观察常见上限是 8 篇，但这次到底拿到几篇，以 `manifest.json` 里的 `sample_count` 为准。平台页面或访问限制变了，脚本可能完全拿不到数据。

## 结果文件怎么看

| 文件 | 里面是什么 |
|---|---|
| `profile.json` | 主页信息和原始数据 |
| `notes_list.json` | 这次看到的笔记列表、互动和封面状态 |
| `covers/` | 成功下载的封面 |
| `meta.json` | 一篇笔记的正文、作者、标签、互动、时间 |
| `desc.md` | 这篇笔记的正文和标签 |
| `images.json` / `imgN.jpg` | 每张笔记图片和下载状态 |
| `manifest.json` | 这次拿到了多少、有没有失败、还缺什么 |

只有 `cover_file` 或 `file` 不为空的图片才是真的下载成功。文件后缀虽然是 `.jpg`，实际可能是 PNG、GIF 或 WebP；`download.format` 会告诉你。脚本只看文件头，真正要识图还得实际打开看。

数字会同时保留原始写法和简单的数值信息。`1.2万` 仍然只是约数，空值仍然是空值。

## 返回码和失败时怎么做

- 返回 `0`：这次平台返回的文字和图片都存好了，不代表已经拿到了整个账号。
- 返回 `1`：链接、请求、页面结构或本地文件有问题。这次不要拿旧结果当新结果。
- 返回 `2`：要么参数没写对，要么文字拿到了但有图片没下载到。看终端报错和 `manifest.json` 区分。

遇到风控、HTTP 失败、详情为空或页面结构变了，就停下来。可以继续用已有材料、用户截图或正文做报告，但要把缺什么写清楚。不要为了凑齐报告一直重试。
