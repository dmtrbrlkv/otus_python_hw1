#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools

# -----------------
# Реализуйте функцию best_hand, которая принимает на вход
# покерную "руку" (hand) из 7ми карт и возвращает лучшую
# (относительно значения, возвращаемого hand_rank)
# "руку" из 5ти карт. У каждой карты есть масть(suit) и
# ранг(rank)
# Масти: трефы(clubs, C), пики(spades, S), червы(hearts, H), бубны(diamonds, D)
# Ранги: 2, 3, 4, 5, 6, 7, 8, 9, 10 (ten, T), валет (jack, J), дама (queen, Q), король (king, K), туз (ace, A)
# Например: AS - туз пик (ace of spades), TH - дестяка черв (ten of hearts), 3C - тройка треф (three of clubs)

# Задание со *
# Реализуйте функцию best_wild_hand, которая принимает на вход
# покерную "руку" (hand) из 7ми карт и возвращает лучшую
# (относительно значения, возвращаемого hand_rank)
# "руку" из 5ти карт. Кроме прочего в данном варианте "рука"
# может включать джокера. Джокеры могут заменить карту любой
# масти и ранга того же цвета, в колоде два джокерва.
# Черный джокер '?B' может быть использован в качестве треф
# или пик любого ранга, красный джокер '?R' - в качестве черв и бубен
# любого ранга.

# Одна функция уже реализована, сигнатуры и описания других даны.
# Вам наверняка пригодится itertoolsю
# Можно свободно определять свои функции и т.п.
# -----------------


def hand_rank(hand):
    """Возвращает значение определяющее ранг 'руки'"""
    ranks = card_ranks(hand)
    if straight(ranks) and flush(hand):
        return (8, max(ranks))
    elif kind(4, ranks):
        return (7, kind(4, ranks), kind(1, ranks))
    elif kind(3, ranks) and kind(2, ranks):
        return (6, kind(3, ranks), kind(2, ranks))
    elif flush(hand):
        return (5, ranks)
    elif straight(ranks):
        return (4, max(ranks))
    elif kind(3, ranks):
        return (3, kind(3, ranks), ranks)
    elif two_pair(ranks):
        return (2, two_pair(ranks), ranks)
    elif kind(2, ranks):
        return (1, kind(2, ranks), ranks)
    else:
        return (0, ranks)


def card_ranks(hand):
    """Возвращает список рангов (его числовой эквивалент),
    отсортированный от большего к меньшему"""

    rank_dict = {
        "T": 10,
        "J": 11,
        "Q": 12,
        "K": 13,
        "A": 14
    }
    ranks = []
    for card in hand:
        if card[0].isdigit():
            ranks.append(int(card[0]))
        else:
            ranks.append(rank_dict[card[0]])
    ranks.sort(reverse=True)
    return ranks


def flush(hand):
    """Возвращает True, если все карты одной масти"""
    return all_equal([card[1] for card in hand])

def straight(ranks):
    """Возвращает True, если отсортированные ранги формируют последовательность 5ти,
    где у 5ти карт ранги идут по порядку (стрит)"""
    cur_rank = None
    for rank in ranks:
        if cur_rank and cur_rank != (rank + 1):
            return False
        cur_rank = rank
    return True


def kind(n, ranks):
    """Возвращает первый ранг, который n раз встречается в данной руке.
    Возвращает None, если ничего не найдено"""

    ranks_n = itertools.combinations(ranks, n)
    for rank_n in ranks_n:
        if all_equal(rank_n):
            # если нашли n одинаковых, то проеряем, нет ли таких же n+1 одинаковых
            rank_n1 = kind(n+1, ranks)
            if not rank_n1 or rank_n1 != rank_n[0]:
                return rank_n[0]
    return None


def two_pair(ranks):
    """Если есть две пары, то возврщает два соответствующих ранга,
    иначе возвращает None"""
    rank1 = None
    rank2 = None
    ranks_2 = itertools.combinations(ranks, 2)
    for rank_2 in ranks_2:
        if all_equal(rank_2):
            if not rank1:
                #нашли первую пару
                rank1 = rank_2[0]
            else:
                # нашли вторую пару
                rank2 = rank_2[0]
                return rank1, rank2
    return None


def compare_hand_rank(rank1, rank2):
    for x,y in zip(rank1, rank2):
        if isinstance(x, list):
            if compare_hand_rank(x, y):
                return True
        elif x < y:
            return False
        elif x > y:
            return True
    return False


def all_equal(iterable):
    "Returns True if all the elements are equal to each other"
    g = itertools.groupby(iterable)
    return next(g, True) and not next(g, False)


def best_hand(hand):
    """Из "руки" в 7 карт возвращает лучшую "руку" в 5 карт """

    all_hand5 = get_hand5(hand)
    best_rank = [0]
    best_hand = None
    for hand5 in all_hand5:
        rank = hand_rank(hand5)
        if compare_hand_rank(rank, best_rank):
            best_rank = rank
            best_hand = hand5
    return best_hand


def get_hand5(hand):
    """комбинации из 5 карт"""
    return itertools.combinations(hand, 5)


def get_hand5_with_joker(hand):
    """получает все варианты руки из 7 карт с замененными джокерами и возвращает комбинации по 5 карт"""
    for new_hand in get_replaced_jokers_hands(hand):
        for hand5 in get_hand5(new_hand):
            yield hand5


def get_joker_deck(hand, joker):
    """карты, на которые может замениться джокер"""
    ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
    red_suits = ["H", "D"]
    black_suits = ["C", "S"]

    if joker[1] == "R":
        suits = red_suits
    else:
        suits = black_suits

    joker_deck = filter(lambda card: False if card in hand else True, [rank + suit for suit in suits for rank in ranks])
    return joker_deck


def replace_joker(hand, joker):
    """генерирует руки с замененным джокером, если джокера нет, то возвращается переданная колода"""
    if joker in hand:
        joker_deck = get_joker_deck(hand, joker)
        for new_card in joker_deck:
            new_hand = [new_card if (card == joker) else card for card in hand]
            yield new_hand
    else:
        yield hand


def get_replaced_jokers_hands(hand):
    """генерирует руки с замененными джокерами"""
    for instead_red_joker_hand in replace_joker(hand, "?R"):
        for instead_black_joker_hand in replace_joker(instead_red_joker_hand, "?B"):
            yield instead_black_joker_hand


def best_wild_hand(hand):
    """best_hand но с джокерами"""

    all_hand5 = get_hand5_with_joker(hand)

    best_rank = [0]
    best_hand = None
    for hand5 in all_hand5:
        rank = hand_rank(hand5)
        if compare_hand_rank(rank, best_rank):
            best_rank = rank
            best_hand = hand5
    return best_hand


def test_best_hand():
    print("test_best_hand...")
    assert (sorted(best_hand("6C 7C 8C 9C TC 5C JS".split()))
            == ['6C', '7C', '8C', '9C', 'TC'])
    assert (sorted(best_hand("TD TC TH 7C 7D 8C 8S".split()))
            == ['8C', '8S', 'TC', 'TD', 'TH'])
    assert (sorted(best_hand("JD TC TH 7C 7D 7S 7H".split()))
            == ['7C', '7D', '7H', '7S', 'JD'])
    print('OK')


def test_best_wild_hand():
    print("test_best_wild_hand...")
    assert (sorted(best_wild_hand("6C 7C 8C 9C TC 5C ?B".split()))
            == ['7C', '8C', '9C', 'JC', 'TC'])
    assert (sorted(best_wild_hand("TD TC 5H 5C 7C ?R ?B".split()))
            == ['7C', 'TC', 'TD', 'TH', 'TS'])
    assert (sorted(best_wild_hand("JD TC TH 7C 7D 7S 7H".split()))
            == ['7C', '7D', '7H', '7S', 'JD'])
    print('OK')


if __name__ == '__main__':
    test_best_hand()
    test_best_wild_hand()
