"""小红书轻量 SSR 采集公共函数；标准库 + curl，失败不重试。"""
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")


class CollectionError(Exception):
    """可交付给用户的脱敏错误，不包含带凭据 URL 或 curl 原始 stderr。"""


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_target(target, kind, token=None):
    target = target.strip()
    source = "pc_user"
    if kind == "profile" and re.fullmatch(r"[0-9a-fA-F]{24}", target):
        identifier = target.lower()
    else:
        try:
            parsed = urlparse(target)
            valid_host = parsed.hostname in {"xiaohongshu.com", "www.xiaohongshu.com", "m.xiaohongshu.com"}
            if (parsed.scheme not in {"http", "https"} or not valid_host or parsed.username
                    or parsed.password or parsed.port not in {None, 80, 443}):
                raise CollectionError("请提供小红书官方域名的账号或笔记完整链接。")
            pattern = (r"/user/profile/([0-9a-fA-F]{24})/?" if kind == "profile"
                       else r"/(?:explore|discovery/item)/([0-9a-fA-F]{24})/?")
            match = re.fullmatch(pattern, parsed.path)
            if not match:
                raise CollectionError("链接缺少对应路由的24位 ID；短链接请先手工打开并复制完整链接。")
            identifier = match.group(1).lower()
            query = parse_qs(parsed.query)
            token = token or query.get("xsec_token", [None])[0]
            source = query.get("xsec_source", [source])[0]
        except ValueError:
            raise CollectionError("链接格式无效。") from None
    if kind == "note" and not token:
        raise CollectionError("链接缺 xsec_token；请提供同篇笔记的带 token 完整链接。")
    route = "user/profile" if kind == "profile" else "discovery/item"
    url = "https://www.xiaohongshu.com/{}/{}".format(route, identifier)
    if token:
        url += "?" + urlencode({"xsec_token": token, "xsec_source": source})
    return identifier, url


def parse_state(html):
    match = re.search(r"(?:window\.)?__INITIAL_STATE__\s*=\s*(.*?)</script\s*>", html, re.DOTALL)
    if not match:
        raise CollectionError("页面无 SSR state；可能风控、链接失效或站点变化。请停止请求。")
    raw = match.group(1).strip().rstrip(";").strip()
    # 只替换字符串之外的 JS undefined，不改变正文中的同名词。
    raw = re.sub(r'"(?:\\.|[^"\\])*"|\bundefined\b',
                 lambda m: "null" if m.group(0) == "undefined" else m.group(0), raw)
    try:
        state = json.loads(raw)
    except json.JSONDecodeError:
        raise CollectionError("SSR state 不是可解析的 JSON；请停止请求并说明数据缺口。") from None
    if not isinstance(state, dict):
        raise CollectionError("SSR state 结构变化，未获得可用对象。")
    return state


def normalize_count(raw):
    result = {"raw": raw, "value": None, "precision": "unknown"}
    if raw is None or isinstance(raw, bool):
        return result
    text = str(raw).strip().replace(",", "").replace("，", "")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([万亿wWkK]?)(\+?)", text)
    if not match:
        return result
    number, unit, plus = match.groups()
    try:
        value = Decimal(number) * {"": 1, "万": 10000, "亿": 100000000,
                                   "w": 10000, "k": 1000}.get(unit.lower(), 1)
    except InvalidOperation:
        return result
    if value != value.to_integral_value():
        return result
    result.update(value=int(value), precision="lower_bound" if plus else "approximate" if unit else "exact")
    return result


def prepare_output(directory):
    out = Path(directory).expanduser().resolve()
    if out == REPO_ROOT or REPO_ROOT in out.parents:
        raise CollectionError("真实账号产物必须写到技能仓库外，请通过 -o 指定独立工作目录。")
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError:
        raise CollectionError("无法创建工作目录，请检查路径和权限。") from None
    return out


def reset_outputs(out, kind):
    """清除本命令的旧产物，防止第二次失败时旧文件冒充当前结果。"""
    names = ["manifest.json"] + (["profile.json", "notes_list.json"] if kind == "profile"
                                  else ["meta.json", "desc.md", "images.json"])
    for name in names:
        (out / name).unlink(missing_ok=True)
    images = out / "covers" if kind == "profile" else out
    if images.is_symlink():
        raise CollectionError("图片目录不能是符号链接，请使用独立工作目录。")
    images.mkdir(parents=True, exist_ok=True)
    pattern = "cover*.jpg*" if kind == "profile" else "img*.jpg*"
    for path in images.glob(pattern):
        if path.is_file() or path.is_symlink():
            path.unlink()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def image_url(raw):
    if not isinstance(raw, str):
        return ""
    return "https:" + raw if raw.startswith("//") else raw


def safe_source(url):
    return url.split("?", 1)[0].split("#", 1)[0]


class RequestClient:
    def __init__(self, interval=1.5):
        if interval < 1 or interval != interval or interval == float("inf"):
            raise CollectionError("请求间隔必须为有限数且至少1秒。")
        self.interval = interval
        self.last_request = None

    def _request(self, url, destination=None):
        try:
            parsed = urlparse(url)
        except ValueError:
            raise CollectionError("图片或页面地址格式无效。") from None
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise CollectionError("图片或页面地址不是有效 HTTPS 地址。")
        if self.last_request is not None:
            wait = self.interval - (time.monotonic() - self.last_request)
            if wait > 0:
                time.sleep(wait)
        command = ["curl", "--silent", "--show-error", "--fail", "--location",
                   "--proto", "=https", "--proto-redir", "=https", "--max-time", "25",
                   "--header", "User-Agent: " + MOBILE_UA]
        if destination is not None:
            command += ["--output", str(destination)]
        command += [url]
        self.last_request = time.monotonic()
        try:
            result = subprocess.run(command, capture_output=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            raise CollectionError("curl 不可用或请求超时；请停止请求，勿自动重试。") from None
        if result.returncode:
            raise CollectionError("请求失败（curl退出码 {}）；请停止请求，勿自动重试。".format(result.returncode))
        return result.stdout

    def fetch_html(self, url):
        html = self._request(url).decode("utf-8", errors="replace")
        if not html.strip():
            raise CollectionError("页面响应为空；请停止请求。")
        return html

    def download(self, url, destination):
        temporary = destination.with_suffix(destination.suffix + ".part")
        destination.unlink(missing_ok=True)
        try:
            self._request(url, temporary)
            with temporary.open("rb") as file:
                header = file.read(16)
            formats = [(header.startswith(b"\xff\xd8\xff"), "jpeg"),
                       (header.startswith(b"\x89PNG\r\n\x1a\n"), "png"),
                       (header.startswith((b"GIF87a", b"GIF89a")), "gif"),
                       (header.startswith(b"RIFF") and header[8:12] == b"WEBP", "webp")]
            image_format = next((name for matches, name in formats if matches), None)
            if not image_format:
                raise CollectionError("响应不是支持的图片文件，可能为风控页面。")
            size = temporary.stat().st_size
            temporary.replace(destination)
            return {"status": "downloaded", "format": image_format, "bytes": size}
        except (CollectionError, OSError) as error:
            message = str(error) if isinstance(error, CollectionError) else "图片文件保存失败。"
            return {"status": "failed", "error": message}
        finally:
            temporary.unlink(missing_ok=True)


def download_images(client, items, out, file_key):
    stopped = False
    for item in items:
        destination = item.pop("destination")
        url = item.pop("download_url")
        if stopped:
            item["download"] = {"status": "skipped", "error": "前一张图片失败，已停止后续请求。"}
        elif not url:
            item["download"] = {"status": "missing", "error": "未获取图片地址。"}
        else:
            item["download"] = client.download(url, out / destination)
            stopped = item["download"]["status"] == "failed"
        item[file_key] = destination if item["download"]["status"] == "downloaded" else None


def finish_manifest(out, manifest, items):
    counts = {status: sum(item["download"]["status"] == status for item in items)
              for status in ("downloaded", "failed", "skipped", "missing")}
    partial = any(counts[status] for status in ("failed", "skipped", "missing"))
    manifest.update(status="partial" if partial else "complete", downloads=counts)
    write_json(out / "manifest.json", manifest)
    print("[partial] 文本数据已保存，图片未完整获取；请查看 manifest.json。" if partial
          else "[ok] 已保存当前样本和 {} 张图片。".format(counts["downloaded"]))
    return 2 if partial else 0
