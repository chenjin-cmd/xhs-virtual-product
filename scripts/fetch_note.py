#!/usr/bin/env python3
"""抓取用户提供的同篇笔记级 xsec_token 链接：正文、互动和图片。

融合自 xhs-account-teardown（MIT），来源声明见 THIRD_PARTY_NOTICES.md。
"""
import argparse
import sys

from xhs_common import (CollectionError, RequestClient, download_images, finish_manifest,
                        image_url, normalize_count, parse_state, parse_target,
                        prepare_output, reset_outputs, safe_source, utc_now, write_json)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="同篇笔记的带 xsec_token 完整链接")
    parser.add_argument("-o", "--out", required=True, help="仓库外的独立工作目录（必填）")
    parser.add_argument("--interval", type=float, default=1.5, help="请求间隔秒数，至少1秒，默认1.5")
    args = parser.parse_args(argv)
    out = None
    manifest = {"schema_version": 1, "kind": "note", "collected_at": utc_now(),
                "scope": "user_supplied_token_note", "unavailable": ["comments", "shop_sales", "profit"]}
    try:
        note_id, url = parse_target(args.url, "note")
        client = RequestClient(args.interval)
        out = prepare_output(args.out)
        reset_outputs(out, "note")
        manifest["source"] = safe_source(url)
        state = parse_state(client.fetch_html(url))
        root = state.get("noteData") or {}
        data = root.get("data") if isinstance(root, dict) else None
        note = data.get("noteData") if isinstance(data, dict) else None
        if not isinstance(note, dict) or note.get("noteId") != note_id:
            raise CollectionError("笔记数据为空、ID不符或结构变化；token可能失效。请停止请求。")
        author = note.get("user") or {}
        interact = note.get("interactInfo") or {}
        if not isinstance(author, dict) or not isinstance(interact, dict):
            raise CollectionError("作者或互动数据结构变化。")
        tags = note.get("tagList") or []
        if not isinstance(tags, list):
            raise CollectionError("笔记标签列表结构变化。")
        meta = {"note_id": note_id, "title": note.get("title"), "type": note.get("type"),
                "author": author.get("nickName"), "author_id": author.get("userId"), "desc": note.get("desc"),
                "tags": [t.get("name") for t in tags if isinstance(t, dict) and t.get("name")],
                "interact": {key: interact.get(key) for key in ("likedCount", "collectedCount", "commentCount", "shareCount")},
                "time": note.get("time"), "last_update": note.get("lastUpdateTime"),
                "source": manifest["source"], "collected_at": manifest["collected_at"]}
        meta["metrics"] = {key: normalize_count(raw) for key, raw in meta["interact"].items()}
        raw_images = note.get("imageList")
        if not isinstance(raw_images, list):
            raise CollectionError("笔记图片列表未获取或结构变化，不能登记为完整图片采集。")
        images = []
        for index, raw in enumerate(raw_images, 1):
            if not isinstance(raw, dict):
                raise CollectionError("笔记图片条目结构变化。")
            images.append({"idx": index, "w": raw.get("width"), "h": raw.get("height"),
                           "source": "笔记第{}页".format(index), "collected_at": manifest["collected_at"],
                           "download_url": image_url(raw.get("url")), "destination": "img{}.jpg".format(index)})
        manifest["sample_count"] = 1
        manifest["image_count"] = len(images)
        download_images(client, images, out, "file")
        write_json(out / "meta.json", meta)
        write_json(out / "images.json", images)
        body = meta["desc"] if meta["desc"] is not None else "未获取"
        (out / "desc.md").write_text("# {}\n\n{}\n\n标签：{}\n".format(
            meta["title"] or "未获取", body, " ".join("#" + tag for tag in meta["tags"])), encoding="utf-8")
        return finish_manifest(out, manifest, images)
    except (CollectionError, OSError) as error:
        message = str(error) if isinstance(error, CollectionError) else "本地文件操作失败，请检查权限和工作目录。"
        print("[error] " + message, file=sys.stderr)
        if out is not None:
            manifest.update(status="failed", error=message)
            try:
                write_json(out / "manifest.json", manifest)
            except OSError:
                pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
