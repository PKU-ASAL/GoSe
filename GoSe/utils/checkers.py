from itertools import product

def assert_sum_equals_one(plist):
    s = sum(plist)
    assert abs(s - 1) < 0.000001, "Sum is not 1: {}\nList: {}".format(s, plist)

def check_condition_homap(condition_homap, option_cnt, history_len):
    # check the size of condition_homap
    correct_size = 0
    for i in range(history_len):
        correct_size += option_cnt ** i
    assert len(condition_homap) == correct_size, "len(condition_homap) = {}, correct_size = {}".format(len(condition_homap), correct_size)
    # for every given history, sum_j(condition_homap[history]) = 1
    for i in range(history_len):
        choices = product(range(option_cnt), repeat=i)
        for choice in choices:
            choice_str = ",".join([str(x) for x in choice])
            assert choice_str in condition_homap
            p_list = []
            for j in range(option_cnt):
                p_list.append(condition_homap[choice_str][str(j)])
            assert_sum_equals_one(p_list)

def check_hmap(hmap, option_cnt, history_len):
    # check the size of hmap
    correct_size = 0
    for i in range(history_len + 1):
        correct_size += option_cnt ** i
    assert len(hmap) == correct_size, "len(hmap) = {}, correct_size = {}".format(len(hmap), correct_size)
    # for every given length, sum_j(hmap[j]) = 1
    for i in range(history_len + 1):
        choices = product(range(option_cnt), repeat=i)
        p_list = []
        for choice in choices:
            choice_str = ",".join([str(x) for x in choice])
            assert choice_str in hmap
            p_list.append(hmap[choice_str])
        assert_sum_equals_one(p_list)

def check_condition_ohmap(condition_ohmap, option_cnt, history_len):
    assert len(condition_ohmap) == option_cnt and option_cnt > 0, "len(condition_ohmap) = {}, option_cnt = {}".format(len(condition_ohmap), option_cnt)
    assert len(condition_ohmap[str(0)]) == history_len
    for j in range(option_cnt):
        assert str(j) in condition_ohmap
        for k in range(history_len):
            p_list = []
            choices = product(range(option_cnt), repeat=k)
            for choice in choices:
                choice_str = ",".join([str(x) for x in choice])
                assert choice_str in condition_ohmap[str(j)][k]
                p_list.append(condition_ohmap[str(j)][k][choice_str])
            assert_sum_equals_one(p_list)

def check_pmap(pmap, option_cnt, history_len):
    # check pmap: for every given i and k, sum_j(pmap[i][j][k]) = 1
    for i in range(option_cnt):
        for k in range(history_len):
            res = 0
            for j in range(option_cnt):
                res += pmap[i][j][k]
            plist = [pmap[i][j][k] for j in range(option_cnt)]
            assert_sum_equals_one(plist)
