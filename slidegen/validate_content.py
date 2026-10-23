"""content.jsonの構造と意味を分けて検証し、生成前に日本語で修正箇所を返す。"""
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from slidegen.input_io import load_content_json
from slidegen.sample_content_guard import sample_reuse_paths
from slidegen.schema_validation import SLIDE_SCHEMAS, envelope_errors, slide_errors
from slidegen.semantic_validation import validate_semantics

_PLACEHOLDER = re.compile(r"^<[^<>]+>$")
_UNRESOLVED = re.compile(r"^(?:TBD|TODO|要確認|未定|仮入力|仮文言)$", re.IGNORECASE)
_TITLE_SENTENCE_MARKS = re.compile(r"[、。！？!?；;]|\r|\n")
_TITLE_PREDICATE_ENDING = re.compile(
    r"(?:る|す|く|ぐ|む|ぶ|ぬ|つ|う|た|だ|ない|なかった|"
    r"できます|できる|できない|必要です|不要です)$"
)
_TITLE_ASSERTIVE_NOUN = re.compile(
    r"(?:を|が|は|では|には).*(?:短縮|削減|増加|減少|上昇|低下|改善|向上|"
    r"実現|確立|統一|明確化|可視化|最適化|自動化)$"
)
_TITLE_ASSERTIVE_QUALITY = re.compile(
    r"(?:が|は|では|には).*(?:重要|必要|不要|有効|無効|可能|不可能|最適|"
    r"優位|劣位|高い|低い|大きい|小さい|困難|容易|べき)$"
)


_TYPE_KEYS = {name: set(schema["properties"]) for name, schema in SLIDE_SCHEMAS.items()}
NOTE_TYPES = {name for name, keys in _TYPE_KEYS.items() if "note" in keys}
_LEAD_ONLY_FIELDS = {
    "scope_boundary": {"assumptions"},
    "paired_comparison": {"takeaway"},
    "relationship_map": {"takeaway"},
    "swimlane_flow": {"takeaway"},
    "message_sequence": {"takeaway"},
    "nw_protocol_flow": {"takeaway"},
    "nw_frame_anatomy": {"takeaway"},
    "config_lab": {"takeaway"},
}



def _is_str(v):
    return isinstance(v, str) and v.strip() != ""



def validation_warnings(deck):
    """エラーとは分けて返す移行警告。入力値や端末固有パスを出さない。"""
    messages = []
    if not isinstance(deck, dict) or not isinstance(deck.get("slides"), list):
        return messages
    for index, slide in enumerate(deck["slides"]):
        if not isinstance(slide, dict) or slide.get("type") != "bullets":
            continue
        items = slide.get("bullets")
        if isinstance(items, list) and any(isinstance(item, list) for item in items):
            messages.append(
                f"slides[{index}].bullets: 旧2要素配列は非推奨です。"
                '各項目を {"text": "本文"} へ移行してください。2.0.0で受理を終了します。')
    return messages


def _title_policy_error(value):
    """通常資料のページタイトルが、見出しではなく主張文なら理由を返す。"""
    if not _is_str(value):
        return None
    title = value.strip()
    if _TITLE_SENTENCE_MARKS.search(value):
        return "読点・句点・改行を含む文章"
    if _TITLE_PREDICATE_ENDING.search(title):
        return "文末が述語になっている文章"
    if _TITLE_ASSERTIVE_NOUN.search(title):
        return "結論や効果を言い切る文章"
    if _TITLE_ASSERTIVE_QUALITY.search(title):
        return "評価や必要性を言い切る文章"
    return None


def _validate_nominal_review(s, title_error):
    """語尾だけによる名詞の誤検知を、対象見出しと理由付きで限定解除する。"""
    review = s.spec.get("title_nominal_review")
    if "title_nominal_review" not in s.spec:
        return False
    title = s.spec.get("title")
    if not (isinstance(review, dict) and set(review) == {"title", "reason"}
            and review.get("title") == title and _is_str(review.get("reason"))
            and 10 <= len(review["reason"].strip()) <= 200
            and isinstance(title, str) and 2 <= len(title.strip()) <= 40):
        s.err("title_nominal_review は現在のtitleと、名詞句と判断した10〜200文字のreasonを指定してください")
        return False
    if (title_error != "文末が述語になっている文章"
            or re.search(r"[をがは]|では|には|でき|です|ます|しない|なかった", title)):
        s.err("title_nominal_review は短い名詞句の語尾誤検知だけに使えます。文章はleadまたは本文へ移してください")
        return False
    return True


def _placeholder_paths(value, path=""):
    if isinstance(value, str) and _PLACEHOLDER.fullmatch(value.strip()):
        yield path or "トップレベル"
    elif isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            yield from _placeholder_paths(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _placeholder_paths(child, f"{path}[{index}]")


def _unresolved_paths(value, path=""):
    if isinstance(value, str) and _UNRESOLVED.fullmatch(value.strip()):
        yield path or "トップレベル"
    elif isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            yield from _unresolved_paths(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _unresolved_paths(child, f"{path}[{index}]")



class _Slide:
    """構造が確定したスライドの意味検証用コンテキスト。"""
    def __init__(self, idx, spec, errors):
        self.idx, self.spec, self.errors = idx, spec, errors

    def err(self, msg):
        self.errors.append(f"slides[{self.idx}] (type={self.spec.get('type', '?')}): {msg}")


VALIDATORS = {name: validate_semantics for name in SLIDE_SCHEMAS}


def _migration_errors(s):
    kind = s.spec.get("type")
    for key in sorted(_LEAD_ONLY_FIELDS.get(kind, set()) if isinstance(kind, str) else set()):
        if key in s.spec:
            s.err(f'"{key}" は下部の注記帯とともに廃止しました。内容は共通フィールド "lead" へ移してください')
    if s.spec.get("type") == "image":
        if "caption" in s.spec:
            s.err('imageの "caption" は廃止済みです。説明は "lead" へ移してください')
        if "source" in s.spec:
            s.err('imageの "source" は廃止済みです。表示枠を削除し、画像の権利情報はCREDITSへ記録してください')
    if s.spec.get("type") == "org" and any(key in s.spec for key in ("top", "pm", "teams", "external")):
        s.err("旧org形式は廃止しました。org.nodes / org.levels / org.edges へ移行してください")


def validate(deck, *, allow_sample_content=False):
    """構造が壊れたスライドでは意味検証を行わない。入力は変更しない。"""
    errors = envelope_errors(deck)
    if not isinstance(deck, dict):
        return errors
    for path in _placeholder_paths(deck):
        errors.append(f"{path}: <...> の入力欄が残っています。資料要件の値へ置き換えてください")
    for path in _unresolved_paths(deck):
        errors.append(f"{path}: 未確定マーカーが残っています。確定値へ置き換えるか、不要な任意フィールド・スライドを削除してください")
    if not allow_sample_content:
        for path, sample_text in sample_reuse_paths(deck):
            errors.append(f'{path}: 回帰検証サンプルの文言と一致します。資料要件と情報源から新規作成してください (一致: "{sample_text}")')
    slides = deck.get("slides")
    if not isinstance(slides, list):
        return errors
    for index, spec in enumerate(slides):
        if not isinstance(spec, dict):
            errors.append(f"slides[{index}]: オブジェクトにしてください")
            continue
        s = _Slide(index, spec, errors)
        _migration_errors(s)
        structure = slide_errors(spec)
        for message in structure:
            s.err(message)
        if not allow_sample_content:
            title_error = _title_policy_error(spec.get("title"))
            reviewed = _validate_nominal_review(s, title_error)
            if title_error and not reviewed:
                s.err(f'"title" は名詞句または短い疑問形の見出しにしてください ({title_error})。結論・因果・行動はsubtitle、leadまたは本文へ移してください')
        if not structure:
            validate_semantics(s)
    return errors


def main(json_path):
    deck = load_content_json(json_path)
    errors = validate(deck)
    for message in validation_warnings(deck):
        print(f"警告: {message}", file=sys.stderr)
    if errors:
        print(f"NG: {Path(json_path).name} に {len(errors)} 件の問題", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        raise SystemExit(1)
    print(f"OK: {Path(json_path).name} ({len(deck['slides'])} slides) 検証通過")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "content.json")
