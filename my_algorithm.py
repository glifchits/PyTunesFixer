'''
Created on Feb 21, 2012
Author: George Lifchits
'''
from __future__ import division

def findclosest(s1, i, s2):
    diff = 0
    found = False
    result = -1

    while not found and diff <= (i // 2):
        try:
            if s1[i] is s2[i + diff]:
                found = True
                result = i + diff
        except IndexError:
            pass

        try:
            if s1[i] is s2[i - diff]:
                found = True
                result = i - diff
        except IndexError:
            pass

        if not found:
            diff += 1

    return result

def normalize_string(string, chars = ' ()[]{}/\|-.,:;!@#$%^&*'):
    string = string.replace('feat', '').lower()
    string = string.replace('original mix', '')
    string = string.replace('original', '')
    for char in chars:
        string = string.replace(char, '')
    return string

def similar(s1, s2):
    total = 0

    s1 = normalize_string(s1)
    s2 = normalize_string(s2)

    if len(s1) < len(s2):
        s1, s2 = s2, s1

    prev_dist = 0

    for i in range(len(s1)):
        j = findclosest(s1, i, s2)

        if j is not -1:
            dist = abs(i - j)
            index = dist / len(s1)

            if prev_dist is dist:
                index = 0

            prev_dist = dist
        else:
            index = 1

        total += index

    return 1 - (total / len(s1))
