#!/usr/bin/env python3
# coding=utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)

__all__ = ['num_to_chnum']


# 基本阿拉伯数字
BASIC_ARABIC_NUMBERS = '0123456789'
# 基本阿拉伯数字的上标表示
BASIC_SUPSCRIPT_NUMBERS = '⁰¹²³⁴⁵⁶⁷⁸⁹'
# 基本中文数字
BASIC_CHINESE_NUMBERS = '零一二三四五六七八九'
# 大写中文数字
BASIC_CAPITAL_CHINESE_NUMBERS = '零壹贰叁肆伍陆柒捌玖'
# 中文位值：千百十
CHINESE_PLACE_VALUE_K_H_T = '千百十'
# 大写中文位值：千百十
CAPITAL_CHINESE_PLACE_VALUE_K_H_T = '仟佰拾'


def as_enum_key(iterable, start=0):
    return {k: i for i, k in enumerate(iterable, start)}


# 阿拉伯数字字符做键，对应的数字做值，的字典
BASIC_ARABIC_NUMBERS_ENUM = as_enum_key(BASIC_ARABIC_NUMBERS)


def num_to_chnum(
    num: int = 0, 
    capital: bool = False,
    _clean=__import__('re').compile('零{2,}').sub
) -> str:
    '''把一个整数转换成一个表示中文数字的字符串

    :param num: 整数
    :param capital: 是否大写，默认值是 False

    :return: 表示中文数字的字符串
    '''
    if num == 0:
        return '零'

    if capital:
        basic_number = BASIC_CAPITAL_CHINESE_NUMBERS
        k_h_t = CAPITAL_CHINESE_PLACE_VALUE_K_H_T
    else:
        basic_number = BASIC_CHINESE_NUMBERS
        k_h_t = CHINESE_PLACE_VALUE_K_H_T

    def _4_digits_to_chnum(n):
        if not n.lstrip('0'):
            return ''
        ls = [basic_number[BASIC_ARABIC_NUMBERS_ENUM[i]] for i in n]
        l = len(n) - 1
        p = k_h_t[-l:]
        for i in range(l):
            if ls[i] != '零':
                ls[i] += p[i]
        return ''.join(ls).rstrip('零')

    n = str(num if num > 0 else -num)
    ln_n = len(n)
    q, r = divmod(ln_n, 4)
    has_r = r > 0
    ln_ls = q + has_r + 1
    ls = [''] * ln_ls

    if num < 0:
        ls[0] = '负'

    i = 1
    if has_r:
        ls[i] = _4_digits_to_chnum(n[0:r])
        i += 1

    lf_idx = r
    for i, rl_idx in enumerate(range(lf_idx + 4, ln_n + 1, 4), i):
        ls[i] = _4_digits_to_chnum(n[lf_idx:rl_idx])
        lf_idx = rl_idx

    for i, idx in enumerate(range(ln_ls-1, 0, -2), 0):
        idx2 = idx - 1
        idx2_value_is_valid = idx2 and ls[idx2]
        if idx2_value_is_valid:
            ls[idx2] += '万'
        if ls[idx] or idx2_value_is_valid:
            ls[idx] += '亿' * i

    return _clean('零', ''.join(ls))

