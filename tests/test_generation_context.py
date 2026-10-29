"""デッキの交互・並列・入れ子生成で状態が漏れないことを検証する。"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import FrozenInstanceError
from threading import Barrier
import unittest

from slidegen import generate
from slidegen.cover_footer import parse_cover_footer_config
from slidegen.generate_from_json import RENDER, build_presentation
from slidegen.generation_context import bind_context, current_context, make_context
from slidegen.layout_fit import FitError


def deck(name, count=2):
    return {"meta": {"title": name, "footer": name, "author": name + "担当"},
            "slides": [{"type": "title", "title": name, "subtitle": "概要"}]
            + [{"type": "bullets", "kicker": "状態分離", "title": "確認項目",
                "bullets": [{"text": name + "の実行条件を確認します。"}]} for _ in range(count - 1)]}


def config(name):
    return parse_cover_footer_config({"cover": {"background_image": None},
                                      "footer": {"text": name + " / {author} / {total}"}})


def text(prs):
    return "\n".join(shape.text for slide in prs.slides for shape in slide.shapes
                     if shape.has_text_frame)


class GenerationContextTests(unittest.TestCase):
    def assert_deck(self, prs, name, count):
        self.assertEqual(len(prs.slides), count)
        self.assertIn(f"{name}設定 / {name}担当 / {count}", text(prs))
        self.assertIn(f"{count:02d} / {count:02d}", text(prs))
        for page, slide in enumerate(prs.slides, 1):
            if page > 1:
                page_text = "\n".join(shape.text for shape in slide.shapes if shape.has_text_frame)
                self.assertIn(f"{page:02d} / {count:02d}", page_text)
        self.assertNotIn("別資料", text(prs))

    def test_alternating_decks_do_not_share_metadata_config_or_count(self):
        original = current_context()
        for name, count in (("資料甲", 2), ("資料乙", 3), ("資料甲", 2)):
            self.assert_deck(build_presentation(deck(name, count), config(name + "設定")), name, count)
            self.assertIs(current_context(), original)
        self.assertFalse(hasattr(generate, "DECK"))
        self.assertFalse(hasattr(generate, "COVER_FOOTER"))

    def test_parallel_generation_is_isolated(self):
        barrier = Barrier(2, timeout=20)
        original = RENDER["bullets"]

        def delayed(slide, spec, page):
            before = current_context()
            if page == 2:
                if before.metadata["title"] == "資料乙":
                    self.assertLess(before.content_bottom, generate.BODY_BOTTOM)
                else:
                    self.assertEqual(before.content_bottom, generate.BODY_BOTTOM)
                barrier.wait()
            original(slide, spec, page)
            self.assertIs(current_context(), before)

        registry = {**RENDER, "bullets": delayed}

        def build(name):
            source = deck(name, 3 if name == "資料乙" else 2)
            if name == "資料乙":
                source["slides"][1]["footnote"] = {"text": "資料乙だけの補足です。"}
            return build_presentation(source, config(name + "設定"), renderers=registry)

        with ThreadPoolExecutor(max_workers=2) as pool:
            outputs = list(pool.map(build, ("資料甲", "資料乙")))
        for prs, name in zip(outputs, ("資料甲", "資料乙")):
            self.assert_deck(prs, name, 3 if name == "資料乙" else 2)
            other = "資料乙" if name == "資料甲" else "資料甲"
            self.assertNotIn(other, text(prs))

    def test_nested_build_restores_outer_footnote_context(self):
        inner = []
        original = current_context()

        def nested(slide, spec, page):
            outer = current_context()
            self.assertLess(outer.content_bottom, generate.BODY_BOTTOM)
            inner.append(build_presentation(deck("別資料", 3), config("内側設定")))
            self.assertIs(current_context(), outer)
            RENDER["bullets"](slide, spec, page)

        outer = deck("資料甲")
        outer["slides"][1]["footnote"] = {"text": "外側の補足です。"}
        result = build_presentation(outer, config("資料甲設定"), renderers={**RENDER, "bullets": nested})
        self.assert_deck(result, "資料甲", 2)
        self.assertIn("内側設定 / 別資料担当 / 3", text(inner[0]))
        self.assertIs(current_context(), original)

    def test_failure_restores_context_and_does_not_exit_process(self):
        original = current_context()

        def failing(*args):
            raise FitError("本文を収容できません")

        source = deck("別資料")
        source["slides"][1]["footnote"] = {"text": "失敗する補足です。"}
        with self.assertRaisesRegex(FitError, r"slides\[1\].*bullets"):
            build_presentation(source, config("失敗設定"), renderers={**RENDER, "bullets": failing})
        self.assertIs(current_context(), original)
        self.assert_deck(build_presentation(deck("資料甲"), config("資料甲設定")), "資料甲", 2)

    def test_context_and_input_snapshot_are_immutable(self):
        source = deck("資料甲")
        expected = deepcopy(source)
        context = make_context(source)
        source["meta"]["title"] = "変更後"
        self.assertEqual(context.metadata["title"], "資料甲")
        with self.assertRaises(TypeError):
            context.metadata["title"] = "変更不可"
        with self.assertRaises(FrozenInstanceError):
            context.theme.FONT = "変更不可"

        def mutate_caller(slide, spec, page):
            expected["meta"]["footer"] = "別資料"
            RENDER["bullets"](slide, spec, page)

        result = build_presentation(expected, renderers={**RENDER, "bullets": mutate_caller})
        self.assertNotIn("別資料", text(result))
        self.assertIn("資料甲", text(result))

    def test_default_config_does_not_inherit_previous_build(self):
        build_presentation(deck("別資料"), config("カスタム設定"))
        result = build_presentation(deck("資料甲"))
        self.assertNotIn("カスタム設定", text(result))
        self.assertIn("資料甲", text(result))

    def test_validation_and_registry_errors_restore_context(self):
        original = current_context()
        invalid = deck("資料甲")
        invalid["slides"][1]["title"] = "入力が不正です"
        with self.assertRaisesRegex(ValueError, "入力に問題"):
            build_presentation(invalid)
        with self.assertRaisesRegex(FitError, "未対応のスライド種別"):
            build_presentation(deck("資料甲"), renderers={})
        self.assertIs(current_context(), original)

    def test_overfull_footnote_reports_position_and_restores_context(self):
        original = current_context()
        source = deck("資料甲")
        source["slides"][1]["footnote"] = {"text": "補足条件" * 120}
        with self.assertRaisesRegex(FitError, r"slides\[1\].*bullets"):
            build_presentation(source)
        self.assertIs(current_context(), original)

    def test_explicit_low_level_context_restores_after_exception(self):
        original = current_context()
        context = make_context(deck("資料甲", 3), config("明示設定"))
        with self.assertRaises(RuntimeError):
            with bind_context(context):
                self.assertEqual(generate.page_label(2), "02 / 03")
                raise RuntimeError("中断")
        self.assertIs(current_context(), original)


if __name__ == "__main__":
    unittest.main()
