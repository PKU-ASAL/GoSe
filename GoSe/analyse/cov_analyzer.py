from GoSe.utils.checkers import assert_sum_equals_one
import logging

def cov_diff_analyzer(s1, s2):
    # check they are all set
    diff_info = dict()
    assert s1 is not None and s2 is not None
    assert isinstance(s1, set) and isinstance(s2, set)
    # get the difference
    s1_more = s1.difference(s2)
    s2_more = s2.difference(s1)
    if len(s1) == 0 and len(s2) == 0:
        diff_info['new_function_flag'] = False
        diff_info['score'] = 0
        return diff_info
    elif len(s1) == 0 and len(s2) > 0:
        diff_info['new_function_flag'] = True
        diff_info['score'] = len(s2)
        return diff_info
    elif len(s1) > 0 and len(s2) == 0:
        diff_info['new_function_flag'] = False
        diff_info['score'] = -len(s1)
        return diff_info
    else:
        diff_info['new_function_flag'] = False
        diff_info['score'] = len(s2_more) - len(s1_more)
        return diff_info

def cov_to_probabilities(old_cov, new_cov_list):
    # check if old_cov and new_cov_list are all set
    assert old_cov is not None and new_cov_list is not None
    assert isinstance(old_cov, set) and isinstance(new_cov_list, list)
    for new_cov in new_cov_list:
        assert isinstance(new_cov, set)
    # get the cov difference info
    l = []
    for i, new_cov in enumerate(new_cov_list):
        diff_info = cov_diff_analyzer(old_cov, new_cov)
        priority_rank = 0 if diff_info['new_function_flag'] else 1
        ele = (priority_rank, diff_info['score'], new_cov, i)
        l.append(ele)
    # sort the new_cov_list by priority_rank first, then by score, in descending order
    new_cov_list_sorted = sorted(l, key=lambda x: (x[0], x[1]), reverse=True)
    # distribute the probabilities
    # S = number of cases
    # T = prob diff between neighbouring cases
    # B = base prob
    # 1 = (B + B + (S-1)T) * S / 2 -> B = 1/S - (S-1)T/2
    # B > 0 -> 1/S - (S-1)T/2 > 0 -> T < 2/[S(S-1)]
    # T = 1/[S(S-1)]
    # B = 1/2S
    new_cov_list_cnt = len(new_cov_list)
    assert new_cov_list_cnt > 1, "Error in distributing probs: only one new cov."

    # 2. score-probability
    prob_list = []
    old_function_cov_list = []
    new_function_cov_list = []
    for i in range(new_cov_list_cnt):
        if new_cov_list_sorted[i][0] == 1:
            old_function_cov_list.append(new_cov_list_sorted[i])
        else:
            assert new_cov_list_sorted[i][0] == 0, "Bad priority: {}".format(new_cov_list_sorted[i][0])
            new_function_cov_list.append(new_cov_list_sorted[i])
    assert len(old_function_cov_list) + len(new_function_cov_list) == len(new_cov_list_sorted)
    if len(old_function_cov_list) == 0 and len(new_function_cov_list) == 0:
        assert False, "Unreachable"
    elif len(old_function_cov_list) > 0 and len(new_function_cov_list) == 0:
        NEW_PROBSUM = 0
        OLD_PROBSUM = 1 - NEW_PROBSUM
    elif len(old_function_cov_list) == 0 and len(new_function_cov_list) > 0:
        NEW_PROBSUM = 1
        OLD_PROBSUM = 1 - NEW_PROBSUM
    else:
        NEW_PROBSUM = 0.1
        OLD_PROBSUM = 1 - NEW_PROBSUM
    assert OLD_PROBSUM >= 0 and NEW_PROBSUM >= 0 and OLD_PROBSUM + NEW_PROBSUM == 1, "Bad probabilty: OLD_PROBSUM: {}, NEW_PROBSUM: {}".format(OLD_PROBSUM, NEW_PROBSUM)
    old_function_prob_list = []
    new_function_prob_list = []
    if len(old_function_cov_list) > 0:
        assert OLD_PROBSUM > 0
        delta = 0
        for i in range(len(old_function_cov_list)):
            prob = old_function_cov_list[i][1]
            if prob < 0:
                prob = 0
                delta = 1
            old_function_prob_list.append(prob)
        old_function_prob_list = [p + delta for p in old_function_prob_list]
        old_s = sum(old_function_prob_list)
        if old_s == 0:
            old_function_prob_list = [p + 1 for p in old_function_prob_list]
            old_s = sum(old_function_prob_list)
        assert old_s != 0, "old_s: {}, old_function_prob_list: {}".format(old_s, str(old_function_prob_list))
        old_function_prob_list = [p/old_s * OLD_PROBSUM for p in old_function_prob_list]
    if len(new_function_cov_list) > 0:
        assert NEW_PROBSUM > 0
        delta = 0
        for i in range(len(new_function_cov_list)):
            prob = new_function_cov_list[i][1]
            if prob < 0:
                prob = 0
                delta = 1
            new_function_prob_list.append(prob)
        new_function_prob_list = [p + delta for p in new_function_prob_list]
        new_s = sum(new_function_prob_list)
        if new_s == 0:
            new_function_prob_list = [p + 1 for p in new_function_prob_list]
            new_s = sum(new_function_prob_list)
        assert new_s != 0, "new_s: {}, new_function_prob_list: {}".format(new_s, str(new_function_prob_list))
        new_function_prob_list = [p/new_s * NEW_PROBSUM for p in new_function_prob_list]
    prob_list = old_function_prob_list + new_function_prob_list
    assert_sum_equals_one(prob_list)
    result = [0.0] * new_cov_list_cnt
    for i, ele in enumerate(new_cov_list_sorted):
        result[ele[3]] = prob_list[i]
    assert_sum_equals_one(result)
    return result