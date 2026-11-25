from django.test import SimpleTestCase

from tgbot import fields as f


class PriceTests(SimpleTestCase):
    def test_parses_common_formats(self):
        for raw, expected in (
            ('91 000 $', 91000),
            ('91000', 91000),
            ('87 000', 87000),
            ('91т$', 91000),
            ('91к', 91000),
        ):
            with self.subTest(raw=raw):
                self.assertEqual(f.parse_price_usd(raw), expected)

    def test_rejects_empty_and_zero(self):
        for raw in ('', 'договорная', '0'):
            with self.subTest(raw=raw), self.assertRaises(f.FieldError):
                f.parse_price_usd(raw)

    def test_formatting(self):
        self.assertEqual(f.format_usd(91000), '91 000 $')
        self.assertEqual(f.format_kgs(7962500), '7 962 500 сом')


class AreaRoomsPhoneTests(SimpleTestCase):
    def test_area(self):
        self.assertEqual(f.parse_area('67'), 67)
        self.assertEqual(f.parse_area('69 кв.м'), 69)
        self.assertEqual(f.parse_area('70 м²'), 70)
        with self.assertRaises(f.FieldError):
            f.parse_area('много')

    def test_rooms(self):
        self.assertEqual(f.parse_rooms('2'), 2)
        with self.assertRaises(f.FieldError):
            f.parse_rooms('два')

    def test_phone(self):
        self.assertEqual(f.normalize_phone('0509 349 199'), '0509 349 199')
        self.assertEqual(f.normalize_phone('+996 (509) 349-199'), '+996 (509) 349-199')
        for bad in ('123', 'звоните', '0509<script>'):
            with self.subTest(bad=bad), self.assertRaises(f.FieldError):
                f.normalize_phone(bad)


class TextTests(SimpleTestCase):
    def test_description_keeps_paragraphs(self):
        text = '  Срочно! Продаю!\n\nДОМ Премиум Класса\nОтличный вариант  '
        self.assertEqual(f.clean_description(text), 'Срочно! Продаю!\n\nДОМ Премиум Класса\nОтличный вариант')

    def test_clean_line_collapses_whitespace(self):
        self.assertEqual(f.clean_line('  мкр.   Асанбай ', 255, 'Район'), 'мкр. Асанбай')
        with self.assertRaises(f.FieldError):
            f.clean_line('   ', 255, 'Район')

    def test_split_text_respects_limit(self):
        text = '\n'.join(['строка ' * 50] * 30)
        chunks = f.split_text(text, 1000)
        self.assertTrue(all(len(c) <= 1000 for c in chunks))
        self.assertEqual(''.join(chunks).replace('\n', ''), text.replace('\n', ''))


class PhotoOrderTests(SimpleTestCase):
    def test_full_and_partial_order(self):
        self.assertEqual(f.parse_photo_order('3 1 2', 3), [2, 0, 1])
        self.assertEqual(f.parse_photo_order('4', 4), [3, 0, 1, 2])

    def test_invalid_order(self):
        for raw in ('', '5', '1 1', '0'):
            with self.subTest(raw=raw), self.assertRaises(f.FieldError):
                f.parse_photo_order(raw, 3)
