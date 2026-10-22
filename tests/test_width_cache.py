"""文字幅cacheのキー・上限・実測値の不変性を確認する。"""
from dataclasses import replace
import unittest
from unittest.mock import patch

from slidegen import textfit as t
from slidegen.font_config import FontFace


class WidthCacheTests(unittest.TestCase):
    def setUp(self):
        t._cached_width.cache_clear()

    def tearDown(self):
        t._cached_width.cache_clear()

    def test_same_measurement_is_reused(self):
        face = FontFace("regular.ttf", 0, "Noto Sans JP", "Regular", (400,))
        with patch.object(t, "font_face", return_value=face), patch.object(t, "_measure_width", return_value=1.5) as measure:
            self.assertEqual(t.text_width_in("本文", 12), 1.5)
            self.assertEqual(t.text_width_in("本文", 12), 1.5)
            self.assertEqual(measure.call_count, 1)
            self.assertEqual(t._cached_width.cache_info().hits, 1)

    def test_path_index_axes_and_style_are_not_mixed(self):
        original = FontFace("regular.ttf", 0, "Noto Sans JP", "Regular", (400,))
        cases = [original, replace(original, path="other.ttf"), replace(original, index=2),
                 replace(original, axes=(700,)), replace(original, style="Bold"),
                 replace(original, family="Noto Sans CJK JP")]
        with patch.object(t, "_measure_width", side_effect=range(len(cases))) as measure:
            for index, face in enumerate(cases):
                with patch.object(t, "font_face", return_value=face):
                    self.assertEqual(t.text_width_in("本文", 12), index)
            self.assertEqual(measure.call_count, len(cases))

    def test_size_weight_safety_and_engine_are_part_of_key(self):
        face = FontFace("regular.ttf", 0, "Noto Sans JP", "Regular")
        with patch.object(t, "font_face", return_value=face), patch.object(t, "_measure_width", return_value=1) as measure:
            t.text_width_in("本文", 12)
            t.text_width_in("本文", 13)
            t.text_width_in("本文", 12, "medium")
            with patch.object(t, "width_safety", return_value=1.09):
                t.text_width_in("本文", 12)
            with patch.object(t, "MEASUREMENT_LAYOUT", 99):
                t.text_width_in("本文", 12)
            self.assertEqual(measure.call_count, 5)

    def test_large_text_is_not_retained_and_entry_count_is_bounded(self):
        face = FontFace("regular.ttf", 0, "Noto Sans JP", "Regular")
        with patch.object(t, "font_face", return_value=face), patch.object(t, "_measure_width", return_value=1):
            text = "文" * (t.WIDTH_CACHE_TEXT_LIMIT + 1)
            t.text_width_in(text, 12)
            t.text_width_in(text, 12)
            self.assertEqual(t._cached_width.cache_info().currsize, 0)
            for index in range(t.WIDTH_CACHE_ENTRIES + 10):
                t.text_width_in(str(index), 12)
            self.assertEqual(t._cached_width.cache_info().currsize, t.WIDTH_CACHE_ENTRIES)
            before = t._cached_width.cache_info().misses
            t.text_width_in("0", 12)
            self.assertEqual(t._cached_width.cache_info().misses, before + 1)

    def test_cached_and_uncached_values_are_identical(self):
        for weight in ("regular", "bold", "code"):
            face = t.font_face(weight)
            for size in (10.5, 12, 24):
                for text in ("API 012.3", "WWW iii", "日本語API" if weight != "code" else "show vlan"):
                    expected = t._measure_width(text, size, weight, face, t.width_safety(weight), t.MEASUREMENT_LAYOUT)
                    self.assertEqual(t.text_width_in(text, size, weight), expected)
        self.assertEqual(t.text_width_in("", 12), 0)
        with self.assertRaisesRegex(ValueError, "ウェイト"):
            t.text_width_in("text", 12, "invalid")


if __name__ == "__main__":
    unittest.main()
