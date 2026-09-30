#!/usr/bin/env python3
"""抓取主页 SSR 当前第一页；不获取分页、评论、店铺、销量或全文。

融合自 xhs-account-teardown（MIT），来源声明见 THIRD_PARTY_NOTICES.md。
"""
import argparse
import sys

from xhs_common import (CollectionError, RequestClient, download_images, finish_manifest,
                        image_url, normalize_count, parse_state, parse_target,
                        prepare_output, reset_outputs, safe_source, utc_now, write_json)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="完整账号链接或24位 user_id")
    parser.add_argument("-o", "--out", required=True, help="仓库外的独立工作目录（必填）")
    parser.add_argument("--interval", type=float, default=1.5, help="请求间隔秒数，至少1秒，默认1.5")
    args = parser.parse_args(argv)
    out = None
    manifest = {"schema_version": 1, "kind": "profile", "collected_at": utc_now(),
                "scope": "anonymous_profile_first_page",
                "unavailable": ["full_history", "note_body", "comments", "shop_sales", "profit"]}
    try:
        user_id, url = parse_target(args.target, "profile")
        client = RequestClient(args.interval)
        out = prepare_output(args.out)
        reset_outputs(out, "profile")
        manifest["source"] = safe_source(url)
        state = parse_state(client.fetch_html(url))
        profile_state = state.get("profile")
        if not isinstance(profile_state, dict):
            raise CollectionError("未获取主页 profile；可能链接失效、风控或页面结构变化。")
        user = profile_state.get("userInfo")
        raw_notes = profile_state.get("noteData")
        if not isinstance(user, dict) or not user or not isinstance(raw_notes, list):
            raise CollectionError("主页用户信息或笔记列表结构变化，不能登记为成功。")
        collections = profile_state.get("noteCollectionList") or []
        if not isinstance(collections, list):
            raise CollectionError("主页合集列表结构变化，不能登记为成功。")
        profile = {
            "user_id": user_id, "nickname": user.get("nickname"), "red_id": user.get("redId"),
            "desc": user.get("desc"), "follows": user.get("follows"), "fans": user.get("fans"),
            "like_and_collect": user.get("likeAndCollect"),
            "collections": [c.get("name") for c in collections if isinstance(c, dict)],
            "source": manifest["source"], "collected_at": manifest["collected_at"],
        }
        profile["metrics"] = {key: normalize_count(profile[key]) for key in ("follows", "fans", "like_and_collect")}
        notes = []
        for index, raw in enumerate(raw_notes, 1):
            if not isinstance(raw, dict):
                raise CollectionError("主页列表包含未知条目结构，采集已停止。")
            cover = raw.get("cover") or {}
            url_i = image_url(cover.get("url") if isinstance(cover, dict) else None)
            note = {"idx": index, "id": raw.get("id"), "title": raw.get("title"), "type": raw.get("type"),
                    "likes": raw.get("likes"), "collects": raw.get("collects"), "comments": raw.get("comments"),
                    "sticky": raw.get("sticky"), "source": "主页列表第{}条".format(index),
                    "collected_at": manifest["collected_at"], "warnings": [],
                    "download_url": url_i, "destination": "covers/cover{}.jpg".format(index)}
            note["metrics"] = {key: normalize_count(note[key]) for key in ("likes", "collects", "comments")}
            if note["metrics"]["collects"]["value"] == 0:
                note["warnings"].append("collects_zero_unverified")
            notes.append(note)
        manifest["sample_count"] = len(notes)
        download_images(client, notes, out, "cover_file")
        write_json(out / "profile.json", profile)
        write_json(out / "notes_list.json", notes)
        return finish_manifest(out, manifest, notes)
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
