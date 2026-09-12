"""Carry a pre-memory NekoHub desktop config forward, without its old secrets.

What moves: the settings that took effort to build — RSS feeds, AI task prompts,
mail and wallet endpoints, poll intervals, UI preferences.

What does not move: every credential. The old file is a year old, lives in a
synced folder, and its keys should be treated as burned. Endpoint and account
fields are kept so only the password or key has to be retyped, and the fields
that exist solely to hold a secret (webhooks, bot tokens) are dropped entirely.

    python pc/migrate_legacy_config.py <old config.json> [--apply]

Prints a plan by default; --apply writes pc/config.json after backing it up.
"""
import argparse
import json
import shutil
import time
from pathlib import Path

# Copied as-is: preferences and intervals, nothing sensitive.
PLAIN = ("language", "forward_mode", "filter_mode", "filter_keywords", "toast_duration",
         "poll_seconds", "sound_enabled", "ai_system_prompt", "ai_chat_context_limit",
         "plugin_rss_poll_mins", "plugin_imap_poll_mins", "plugin_web3_poll_mins",
         "plugin_imap_fetch_limit")
# Dropped: these fields are a credential, or are useless without one.
DROPPED = ("gotify_recv_token", "gotify_send_token", "dingtalk_webhook", "dingtalk_secret",
           "tg_bot_token", "tg_chat_id", "email_pass", "ai_api_key", "ai_profiles",
           "forward_enabled", "forward_rss", "forward_imap", "forward_web3")
SECRET_KEYS = ("in_pass", "out_pass", "key")


def load_list(values):
    """The desktop app stores plugin rows as JSON strings inside a JSON list."""
    out = []
    for item in values or []:
        try:
            out.append(json.loads(item) if isinstance(item, str) else dict(item))
        except (TypeError, ValueError):
            continue
    return out


def dump_list(values):
    return [json.dumps(value, ensure_ascii=False) for value in values]


def strip_secrets(rows):
    cleared = 0
    for row in rows:
        for key in SECRET_KEYS:
            if row.get(key):
                row[key] = ""
                cleared += 1
    return rows, cleared


def migrate(old, current):
    """Returns (new settings, human-readable notes). Never invents a credential."""
    new = dict(current)
    notes = []
    for key in PLAIN:
        if key in old:
            new[key] = old[key]
    notes.append(f"偏好与轮询设置：{len(PLAIN)} 项")

    tasks = [t for t in (old.get("ai_tasks") or []) if isinstance(t, dict) and t.get("prompt")]
    for task in tasks:
        task["enabled"] = False  # nothing reruns on its own until you look at it
    new["ai_tasks"] = tasks
    notes.append(f"AI 任务：{len(tasks)} 个（提示词保留，全部设为停用）")

    feeds = load_list(old.get("plugin_rss_urls"))
    new["plugin_rss_urls"] = dump_list(feeds)
    notes.append(f"RSS 订阅：{len(feeds)} 个（公开地址，无凭据）")

    accounts, cleared = strip_secrets(load_list(old.get("plugin_imap_accs")))
    new["plugin_imap_accs"] = dump_list(accounts)
    notes.append(f"邮箱账户：{len(accounts)} 个（服务器与用户名保留，{cleared} 个密码字段已清空，需重新填写）")

    wallets, cleared = strip_secrets(load_list(old.get("plugin_web3_addrs")))
    new["plugin_web3_addrs"] = dump_list(wallets)
    notes.append(f"链上地址：{len(wallets)} 个（地址与链保留，{cleared} 个 API Key 已清空）")

    present = [key for key in DROPPED if old.get(key)]
    notes.append(f"未迁移的凭据字段：{', '.join(present) if present else '无'}")
    return new, notes


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("old", type=Path)
    parser.add_argument("--target", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    old = json.loads(args.old.read_text(encoding="utf-8-sig"))
    current = json.loads(args.target.read_text(encoding="utf-8-sig")) if args.target.exists() else {}
    new, notes = migrate(old, current)
    print("\n".join("- " + note for note in notes))
    if not args.apply:
        print("\n预览模式，未写入。确认无误后加 --apply。")
        return
    if args.target.exists():
        backup = args.target.with_suffix(f".backup-{time.strftime('%Y%m%d-%H%M%S')}.json")
        shutil.copy2(args.target, backup)
        print("\n已备份原配置：" + backup.name)
    args.target.write_text(json.dumps(new, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已写入：" + str(args.target))
    print("模型与 Gotify 的新配置请在界面里填写；本脚本不会替你写入任何密钥。")


if __name__ == "__main__":
    main()
