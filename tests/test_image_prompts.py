"""共通画像プロンプトの結合と安全なCLIを確認する。"""
from copy import deepcopy
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest

from PIL import Image
from slidegen.cover_footer import load_cover_footer_config


SCRIPT = Path(__file__).resolve().parents[1] / '.agents/skills/pptxdsl/scripts/build_image_prompts.py'
build_prompts = runpy.run_path(str(SCRIPT))['build_prompts']
STYLE = dict(palette='#182C43、#0D7870',
             drawing='均一な輪郭線のフラット図解', lettering='読みやすい日本語ゴシック',
             composition='横長、外周の余白を揃える', avoid='影、発光、質感、架空のロゴ')
BRIEFS = [dict(id='role', intent='役割の区別', elements=['スライド', '図解'],
               relationships=['スライド内へ図解を配置'], labels=['図解']),
          dict(id='flow', intent='生成と再利用', elements=['生成画像', 'PPTX'],
               relationships=['採用画像をPPTXへ埋め込む'], labels=['生成画像', 'PPTX'])]


class ImagePromptTests(unittest.TestCase):
    def test_every_prompt_has_identical_style_and_literal_labels(self):
        result = build_prompts(STYLE, BRIEFS)
        for item, brief in zip(result['prompts'], BRIEFS):
            self.assertTrue(item['prompt'].startswith(result['common_prompt'] + '\n\n'))
            self.assertEqual(item['style_sha256'], result['style_sha256'])
            for label in brief['labels']:
                self.assertIn(label, item['prompt'])
        self.assertIn(f'#{load_cover_footer_config().slide.background_color}', result['common_prompt'])
        self.assertFalse(result['prompts'][0]['transparent_background'])
        changed = dict(STYLE, drawing='単色の線画')
        self.assertNotEqual(result['style_sha256'], build_prompts(changed, BRIEFS)['style_sha256'])

    def test_config_background_overrides_no_separate_style_color(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'template.json'
            config.write_text(json.dumps({'slide': {'background_color': 'e0eefF'}}), encoding='utf-8')
            result = build_prompts(STYLE, BRIEFS, template_config=config)
            self.assertIn('#E0EEFF', result['common_prompt'])
            self.assertNotIn('#F7F5EF', result['common_prompt'])
            first_digest = result['style_sha256']
            config.write_text(json.dumps({'slide': {'background_color': 'FFFFFF'}}), encoding='utf-8')
            self.assertNotEqual(first_digest, build_prompts(STYLE, BRIEFS, template_config=config)['style_sha256'])
            config.write_text(json.dumps({'slide': {'background_color': 'not-a-color'}}), encoding='utf-8')
            with self.assertRaises(ValueError):
                build_prompts(STYLE, BRIEFS, template_config=config)

    def test_background_image_requests_real_transparency(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new('RGB', (8, 8), '#E0EEFF').save(root / 'background.png')
            config = root / 'template.json'
            config.write_text(json.dumps({'slide': {'background_color': 'E0EEFF',
                                                     'background_image': 'background.png'}}), encoding='utf-8')
            result = build_prompts(STYLE, BRIEFS, template_config=config)
            self.assertIn('透過PNG', result['common_prompt'])
            self.assertTrue(all(item['transparent_background'] for item in result['prompts']))
            self.assertNotIn(str(root), json.dumps(result, ensure_ascii=False))

    def test_invalid_inputs(self):
        invalid_briefs = [[], [{}], BRIEFS * 2, [dict(BRIEFS[0], id='../escape')],
                          [dict(BRIEFS[0], palette='赤')], [dict(BRIEFS[0], labels='文字')],
                          [dict(BRIEFS[0], intent='')], [dict(BRIEFS[0], elements=[])]]
        for briefs in invalid_briefs:
            with self.subTest(briefs=briefs), self.assertRaises(ValueError):
                build_prompts(STYLE, briefs)
        for style in ({}, dict(STYLE, background='#F7F5EF'), dict(STYLE, palette=''), dict(STYLE, other='上書き')):
            with self.subTest(style=style), self.assertRaises(ValueError):
                build_prompts(style, BRIEFS)

    def test_cli_and_no_overwrite_or_private_path_in_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, data in [('style', STYLE), ('briefs', deepcopy(BRIEFS))]:
                (root / f'{name}.json').write_text(json.dumps(data), encoding='utf-8')
            command = [sys.executable, str(SCRIPT), '--style', str(root / 'style.json'),
                       '--briefs', str(root / 'briefs.json'), '--output', str(root / 'prompts.json')]
            first = subprocess.run(command, capture_output=True,
                                   env={**os.environ, 'PYTHONIOENCODING': 'cp1252'})
            self.assertEqual(first.returncode, 0, first.stderr)
            original = (root / 'prompts.json').read_bytes()
            second = subprocess.run(command, capture_output=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual((root / 'prompts.json').read_bytes(), original)
            self.assertNotIn(str(root).encode(), second.stderr)
            (root / 'style.json').write_text('{', encoding='utf-8')
            invalid = subprocess.run(command, capture_output=True)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertNotIn(b'Traceback', invalid.stderr)

    def test_bundled_cli_uses_same_config_from_user_working_directory(self):
        from tools.plugin.build import build
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugin, _ = build(root / 'plugin')
            script = plugin / 'skills/pptxdsl/scripts/build_image_prompts.py'
            for name, data in [('style', STYLE), ('briefs', BRIEFS),
                               ('template', {'slide': {'background_color': 'E0EEFF'}})]:
                (root / f'{name}.json').write_text(json.dumps(data), encoding='utf-8')
            command = [sys.executable, '-I', str(script), '--style', 'style.json',
                       '--briefs', 'briefs.json', '--template-config', 'template.json',
                       '--output', 'prompts.json']
            result = subprocess.run(command, cwd=root, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('#E0EEFF', json.loads((root / 'prompts.json').read_text(encoding='utf-8'))['common_prompt'])
            (root / 'template.json').write_text('{', encoding='utf-8')
            failed = subprocess.run(command, cwd=root, capture_output=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertNotIn(str(root).encode(), failed.stderr)
            self.assertNotIn(b'Traceback', failed.stderr)


if __name__ == '__main__':
    unittest.main()
