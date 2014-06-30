'''
Created on Sep 1, 2012
Author: George Lifchits
'''
from discogs_tracklist import *
import unittest


class TestConcatList(unittest.TestCase):

    def setUp(self):
        self.utilities = Utilities()

    def test_list_of_one(self):
        expected = 'A'
        result = self.utilities.concat_list(['A'])
        self.assertEqual(expected, result)

    def test_list_of_two(self):
        expected = 'A & B'
        result = self.utilities.concat_list(['A', 'B'])
        self.assertEqual(expected, result)

    def test_basic(self):
        expected = 'A, B, C & D'
        result = self.utilities.concat_list(['A', 'B', 'C', 'D'])
        self.assertEqual(expected, result)

    def test_int_sort(self):
        expected = '1, 2, 3, 4'
        result = self.utilities.concat_list([1, 3, 2, 4], join_str = ', ')
        self.assertEqual(expected, result)

    def test_str_sort(self):
        expected = '1, 2, 3, 4'
        result = self.utilities.concat_list(['1', '3', '2', '4'], join_str = ', ')
        self.assertEqual(expected, result)

    def test_alphabetic_slashes(self):
        expected = 'Bill Bob/David Dude/Zoppy Zoup'
        lst = ['David Dude', 'Zoppy Zoup', 'Bill Bob']
        result = self.utilities.concat_list(lst, join_str = '/')
        self.assertEqual(expected, result)

    def test_intentional_no_sort(self):
        expected = 'A, B, D, C, B, A, D, C & D'
        lst = ['A', 'B', 'D', 'C', 'B', 'A', 'D', 'C', 'D']
        result = self.utilities.concat_list(lst, sort = False)
        self.assertEqual(expected, result)

    def test_filter_dupes_and_sort(self):
        expected = 'A, B, C & D'
        lst = ['A', 'B', 'D', 'C', 'B', 'A', 'D', 'C', 'D']
        result = self.utilities.concat_list(lst)
        self.assertEqual(expected, result)

class TestValuesInTuple(unittest.TestCase):

    def setUp(self):
        self.utilities = Utilities()

    def test_value_include(self):
        values = ['a']
        include = ['a', 'b', 'c']
        self.assertTrue(self.utilities.values_in_tuple(values, include))

    def test_value_exclude(self):
        values = ['a']
        include = ['a', 'b', 'c']
        exclude = ['x', 'y', 'a']
        self.assertFalse(self.utilities.values_in_tuple(values, include, exclude))

    def test_multiple_values(self):
        values = ['a', 'b', 'c']
        include = ['a']
        exclude = ['d']
        self.assertTrue(self.utilities.values_in_tuple(values, include, exclude))

    def test_multiple_values_exclude(self):
        values = ['a', 'b', 'c']
        include = ['a']
        exclude = ['d', 'b']
        self.assertFalse(self.utilities.values_in_tuple(values, include, exclude))

class TestFixDiscogsName(unittest.TestCase):

    def setUp(self):
        self.utilities = Utilities()

    def test_brackets(self):
        result = self.utilities.fix_discogs_string('Titan (15)')
        self.assertEqual('Titan', result)

    def test_the(self):
        result = self.utilities.fix_discogs_string('XX, The')
        self.assertEqual('The XX', result)

    def test_both(self):
        result = self.utilities.fix_discogs_string('Test, The (22)')
        self.assertEqual('The Test', result)

class TestTrackAndDisc(unittest.TestCase):

    def setUp(self):
        self.utilities = Utilities()

    def test_one_track(self):
        expected = (1, 1)
        self.assertEqual(expected, self.utilities.track_and_disc('1'))

    def test_track_and_disc(self):
        expected = (13, 2)
        self.assertEqual(expected, self.utilities.track_and_disc('2-13'))

    def test_this_disc(self):
        expected = (1, 2)
        self.assertEqual(expected, self.utilities.track_and_disc('1',
                                                              this_disc = '2'))

    def test_vinyl_no_prev(self):
        expected = (2, 2)
        self.assertEqual(expected, self.utilities.track_and_disc('C2'))

    def test_vinyl_prev(self):
        expected = (6, 1)
        self.assertEqual(expected, self.utilities.track_and_disc \
                                   ('B3', last_side_tracks = 3))

class TestTrackRange(unittest.TestCase):

    def setUp(self):
        self.utilities = Utilities()

    def test_integers(self):
        expected = (1, 4)
        result = self.utilities.track_range('1 to 4')
        self.assertEqual(expected, result)

    def test_one_track(self):
        expected = (2, 2)
        result = self.utilities.track_range(2)
        self.assertEqual(expected, result)

    def test_vinyl(self):
        expected = ('A2', 'B4')
        result = self.utilities.track_range('A2 to B4')
        self.assertEqual(expected, result)
