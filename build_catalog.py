#!/usr/bin/env python3
"""Build catalog.json for the 3d-yasan archive search UI.

Reads the salvage manifests (rest/manifest.jsonl, full/manifest.jsonl)
next to this script (or under ASSET_ROOT if set) and emits catalog.json
with one entry per model file on disk.

Usage:
    python3 build_catalog.py
    ASSET_ROOT=/path/to/asset-library/3dyasan python3 build_catalog.py
"""
import json
import os
import re
import sys

ROOT = os.environ.get("ASSET_ROOT") or os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog.json")

GENRES = [
    ("椅子・ソファ", ["椅子", "イス", "チェア", "ソファ", "スツール", "ベンチ"]),
    ("机・テーブル", ["机", "テーブル", "デスク"]),
    ("ベッド・寝具", ["ベッド", "布団", "枕", "寝具", "マットレス"]),
    ("収納・棚", ["棚", "タンス", "収納", "本棚", "ロッカー", "キャビネット", "チェスト", "引き出し"]),
    ("照明", ["ランプ", "照明", "ライト", "電気", "スタンド"]),
    ("キッチン・家電", ["キッチン", "台所", "冷蔵庫", "コンロ", "レンジ", "炊飯", "家電", "テレビ", "パソコン", "エアコン", "ガラケー", "スマホ", "電話", "カメラ", "扇風機", "掃除機"]),
    ("衣類・小物", ["服", "帽子", "靴", "かばん", "バッグ", "傘", "ハンガー", "タオル", "眼鏡", "時計", "財布"]),
    ("文具・日用品", ["ペン", "鉛筆", "ノート", "手帳", "マーカー", "消しゴム", "はさみ", "定規", "ゴミ箱", "洗濯", "トイレ", "風呂", "シャンプー"]),
    ("武器・道具", ["弓", "剣", "刀", "槍", "銃", "盾", "ハンマー", "ドライバー", "のこぎり"]),
    ("建物・室内", ["部屋", "家", "館", "廊下", "玄関", "和室", "洋室", "床", "天井"]),
    ("食べ物・食器", ["食器", "皿", "コップ", "マグ", "食べ物", "料理", "パン", "ケーキ", "弁当"]),
    ("植物", ["植物", "観葉", "花", "木", "草", "プランター"]),
    ("建具・建築", ["ドア", "窓", "扉", "壁", "階段", "柵", "フェンス", "柱", "屋根"]),
    ("乗り物", ["車", "バイク", "自転車", "電車", "船", "飛行機"]),
    ("楽器・ホビー", ["ギター", "ピアノ", "楽器", "ゲーム", "おもちゃ", "本", "雑誌"]),
]


def genre_of(title):
    for name, keys in GENRES:
        if any(k in title for k in keys):
            return name
    return "その他"


def num_key(title):
    m = re.match(r"(\d+)", title)
    return int(m.group(1)) if m else 999999


def load_manifest(rel_dir, source_label):
    path = os.path.join(ROOT, rel_dir, "manifest.jsonl")
    items = {}
    if not os.path.exists(path):
        return items
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            local = rec.get("local_path", "")
            if not local:
                continue
            rel = f"{rel_dir}/{local}"
            if rel in items:
                continue  # duplicate upload entry sharing one file
            title = rec.get("title") or os.path.splitext(os.path.basename(local))[0]
            items[rel] = {
                "title": title,
                "path": rel,
                "format": os.path.splitext(local)[1].lstrip(".").upper(),
                "bytes": rec.get("bytes"),
                "sha256": rec.get("sha256"),
                "source": source_label,
                "genre": genre_of(title),
                "page": rec.get("page_url"),
            }
    return items


def main():
    items = {}
    items.update(load_manifest("full", "Wayback"))
    items.update(load_manifest("rest", "REST"))  # REST wins on path collision
    missing = [p for p in items if not os.path.exists(os.path.join(ROOT, p))]
    if missing:
        print(f"warning: {len(missing)} catalog files not on disk", file=sys.stderr)
    ordered = sorted(items.values(), key=lambda it: (num_key(it["title"]), it["title"]))
    total_bytes = sum(it["bytes"] or 0 for it in ordered)
    catalog = {
        "name": "3d-yasan archive",
        "counts": {
            "items": len(ordered),
            "glb": sum(1 for it in ordered if it["format"] == "GLB"),
            "fbx": sum(1 for it in ordered if it["format"] == "FBX"),
            "bytes": total_bytes,
            "missing_on_disk": len(missing),
        },
        "items": ordered,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {OUT}: {len(ordered)} items, {total_bytes/1e6:.1f} MB total")


if __name__ == "__main__":
    main()
