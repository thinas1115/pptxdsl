"""資料共通の画像スタイルとページ別の説明内容を結合する。画像生成APIは呼ばない。"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


STYLE_FIELDS = ('palette', 'drawing', 'lettering', 'composition', 'avoid')
BRIEF_FIELDS = ('id', 'intent', 'elements', 'relationships', 'labels')


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _slide_config(path):
    for parent in Path(__file__).resolve().parents:
        for root in (parent / 'project', parent):
            if (root / 'slidegen/cover_footer.py').is_file():
                sys.path.insert(0, str(root))
                from slidegen.cover_footer import load_cover_footer_config
                return load_cover_footer_config(path).slide
    raise ValueError('同梱のpptxdsl生成コードが見つかりません')


def build_prompts(style, briefs, *, template_config=None):
    if (not isinstance(style, dict) or set(style) != set(STYLE_FIELDS)
            or not all(_text(style[key]) for key in STYLE_FIELDS)):
        raise ValueError('共通スタイルはpalette/drawing/lettering/composition/avoidを指定してください。背景はPPTXと同じ--template-configから読み込みます')
    if not isinstance(briefs, list) or not briefs:
        raise ValueError('ページ別の説明内容を1件以上指定してください')
    slide = _slide_config(template_config)
    transparent = slide.background_image is not None
    color = f'#{slide.background_color}'
    background = (f'Configの背景画像の上に重ねる透過PNG。背景は透明にし、背景色・白い面・市松模様を描かない。下地の基準色は{color}'
                  if transparent else
                  f'全面を完全な単色{color}にする。Configの本文背景と同じ色。グラデーションや周辺減光を入れない')
    resolved_style = {'background': background, **style}
    common = '\n'.join(['【資料共通スタイル：全ページで固定】']
                       + [f'{key}: {value}' for key, value in resolved_style.items()])
    digest = hashlib.sha256(common.encode('utf-8')).hexdigest()
    prompts, seen = [], set()
    for brief in briefs:
        if not isinstance(brief, dict) or set(brief) != set(BRIEF_FIELDS):
            raise ValueError('各ページはid/intent/elements/relationships/labelsだけを指定してください')
        key = brief['id']
        if not isinstance(key, str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', key) or key in seen:
            raise ValueError('画像idは重複しない英小文字始まりの英数字・ハイフン・下線にしてください')
        if not _text(brief['intent']):
            raise ValueError('各ページのintentを空でない文字列で指定してください')
        for field in ('elements', 'relationships', 'labels'):
            values = brief[field]
            if not isinstance(values, list) or not all(_text(value) for value in values):
                raise ValueError('elements/relationships/labelsは文字列の配列にしてください')
        if not brief['elements']:
            raise ValueError('各ページのelementsを1件以上指定してください')
        seen.add(key)
        detail = json.dumps({field: brief[field] for field in BRIEF_FIELDS if field != 'id'},
                            ensure_ascii=False, indent=2)
        prompt = (common + '\n\n【この図で説明する内容】\n' + detail
                  + '\n\n図はラベルと矢印を含む完成画像にする。labelsは指定どおりの文字で描く。'
                  + '\n説明内容から未知の事実を補わない。全図で共通スタイルを維持し、絵柄を変更しない。')
        prompts.append({'id': key, 'image': f'generated/{key}.png',
                        'transparent_background': transparent,
                        'style_sha256': digest, 'prompt': prompt})
    return {'style': resolved_style, 'common_prompt': common, 'style_sha256': digest, 'prompts': prompts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--style', type=Path, required=True, help='全画像共通のスタイルJSON')
    parser.add_argument('--briefs', type=Path, required=True, help='各ページの説明内容JSON')
    parser.add_argument('--template-config', '--cover-footer-config', type=Path,
                        help='PPTX生成と同じ背景・表紙・フッター設定JSON。省略時もPPTX標準設定を使用')
    parser.add_argument('--output', type=Path, required=True, help='出力プロンプトJSON（上書き不可）')
    args = parser.parse_args()
    try:
        style = json.loads(args.style.read_text(encoding='utf-8-sig'))
        briefs = json.loads(args.briefs.read_text(encoding='utf-8-sig'))
        result = build_prompts(style, briefs, template_config=args.template_config)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    except FileExistsError:
        raise SystemExit('NG: 出力ファイルは既にあります。別の出力名を指定してください') from None
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise SystemExit('NG: 入出力先の権限、文字コード、JSON形式を確認してください') from None
    except ValueError as error:
        raise SystemExit(f'NG: {error}') from None
    except ModuleNotFoundError:
        raise SystemExit('NG: 同梱project/requirements.txtのPython依存を導入してください') from None
    print(f'共通スタイルを適用したプロンプト: {len(result["prompts"])}件')


if __name__ == '__main__':
    main()
