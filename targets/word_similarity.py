import anyascii
import difflib
import re


def fuzzy_word_match(w1, w2):
    """SequenceMatcher ratio for two words (0–1)."""
    return difflib.SequenceMatcher(None, w1, w2).ratio()


def best_word_score(word, candidates):
    """Find the best fuzzy match for a word among candidates."""
    scores = [fuzzy_word_match(word, c) for c in candidates]
    return max(scores, default=0)


def hybrid_similarity(string1, string2):
    words1 = [s.upper() for s in string1.split()]
    words2 = [s.upper() for s in string2.split()]

    if not words1 or not words2:
        return 0.0

    forward = sum(best_word_score(w, words2) for w in words1) / len(words1)
    backward = sum(best_word_score(w, words1) for w in words2) / len(words2)

    return max(forward, backward)


def damerau_levenshtein(s1, s2):
    d = {}
    len1, len2 = len(s1), len(s2)

    for i in range(-1, len1 + 1):
        d[(i, -1)] = i + 1
    for j in range(-1, len2 + 1):
        d[(-1, j)] = j + 1

    for i in range(len1):
        for j in range(len2):
            cost = 0 if s1[i] == s2[j] else 1
            d[(i, j)] = min(
                d[(i - 1, j)] + 1,      # deletion
                d[(i, j - 1)] + 1,      # insertion
                d[(i - 1, j - 1)] + cost # substitution
            )
            # Transposition check
            if i > 0 and j > 0 and s1[i] == s2[j - 1] and s1[i - 1] == s2[j]:
                d[(i, j)] = min(d[(i, j)], d[(i - 2, j - 2)] + cost)

    return d[(len1 - 1, len2 - 1)]


def list_similarity(list1, list2):

    forward = []
    for word in list:



# Examples
pairs = [
    ("hello world", "world hello"),           # reordered
    ("colour scheme", "color skeem"),          # misspelled
    ("machine learning model", "lernin macheen modell"),  # both
    ("apple pie", "orange juice"),             # unrelated
]

for a, b in pairs:
    print(f"{a!r} vs {b!r} => {hybrid_similarity(a, b):.2f}")
