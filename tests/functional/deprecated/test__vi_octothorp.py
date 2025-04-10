# Copyright (C) 2018-2023 The NeoVintageous Team (NeoVintageous).
#
# This file is part of NeoVintageous.
#
# NeoVintageous is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# NeoVintageous is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NeoVintageous.  If not, see <https://www.gnu.org/licenses/>.

from NeoVintageous.tests import unittest


class Test__nv_vi_find_word_rev_InNormalMode(unittest.ViewTestCase):

    def setUp(self):
        super().setUp()
        self.set_option('wrapscan', True)

    def test_select_match(self):
        self.normal('abc\n|abc')
        self.view.run_command('nv_vi_find_word_rev', {'mode': unittest.NORMAL})
        self.assertNormal('|abc\nabc')
        self.assertSearch('|abc|\n|abc|')
        self.assertSearchCurrent('|abc|\nabc')

    def test_select_match_middle(self):
        self.normal('abc\na|bc')
        self.view.run_command('nv_vi_find_word_rev', {'mode': unittest.NORMAL})
        self.assertNormal('|abc\nabc')
        self.assertSearch('|abc|\n|abc|')
        self.assertSearchCurrent('|abc|\nabc')

    def test_select_match_end(self):
        self.normal('abc\nab|c')
        self.view.run_command('nv_vi_find_word_rev', {'mode': unittest.NORMAL})
        self.assertNormal('|abc\nabc')
        self.assertSearch('|abc|\n|abc|')
        self.assertSearchCurrent('|abc|\nabc')

    def test_select_repeat_match(self):
        self.normal('abc\nabc\nfoo\n|abc\nbar')
        self.view.run_command('nv_vi_find_word_rev', {'mode': unittest.NORMAL})
        self.view.run_command('nv_vi_find_word_rev', {'mode': unittest.NORMAL})
        self.assertNormal('|abc\nabc\nfoo\nabc\nbar')
        self.assertSearch('|abc|\n|abc|\nfoo\n|abc|\nbar')
        self.assertSearchCurrent('|abc|\nabc\nfoo\nabc\nbar')

    def test_select_wrap_match(self):
        self.normal('boo\n|abc\nfoo\nabc\nbar')
        self.view.run_command('nv_vi_find_word_rev', {'mode': unittest.NORMAL})
        self.assertNormal('boo\nabc\nfoo\n|abc\nbar')
        self.assertSearch('boo\n|abc|\nfoo\n|abc|\nbar')
        self.assertSearchCurrent('boo\nabc\nfoo\n|abc|\nbar')

    def test_select_no_partial_match(self):
        self.normal('boo\nabc\nabcxabc\n|abc\nbar')
        self.view.run_command('nv_vi_find_word_rev', {'mode': unittest.NORMAL})
        self.assertNormal('boo\n|abc\nabcxabc\nabc\nbar')
        self.assertSearch('boo\n|abc|\nabcxabc\n|abc|\nbar')
        self.assertSearchCurrent('boo\n|abc|\nabcxabc\nabc\nbar')

    def test_select_no_match(self):
        self.normal('boo\nabc\nf|oo\nabc\nbar')
        self.view.run_command('nv_vi_find_word_rev', {'mode': unittest.NORMAL})
        self.assertNormal('boo\nabc\n|foo\nabc\nbar')
        self.assertSearch('boo\nabc\n|foo|\nabc\nbar')
        self.assertSearchCurrent('boo\nabc\n|foo|\nabc\nbar')
