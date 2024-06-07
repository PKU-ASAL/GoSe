from GoSe.info.option_info import OptionInfo
from GoSe.utils.cmdlines import instantiate_path, record_timestamp
from GoSe.utils.env import END_PROB, HISTORY_LEN, Strategies
from GoSe.graph.opft_vertex import OPFTVertex
from GoSe.graph.opft_edge import OPFTEdge
from GoSe.graph.get_probability import get_probability_from_values, get_pmap_from_probability
import GoSe.utils.log
import json
import logging
import os
import random

class OPFT:
    def __init__(self, vertices=[], edges=[], history_len=HISTORY_LEN):
        # vertices: [OPFTVertex1, OPFTVertex2, ...]
        self.vertices = vertices
        self.edges = edges
        # vertex_id: vertex -> id
        self.vertex_id = {}
        # probability: func()
        self.history_len = history_len
        self.probability = None
        self.set_cover = None
        self.posOptions = []
        self.instantiatedPosOptions = []
        self.posPatterns = []
        self.expected_len = -1
        self.attn_scores = None
        self.d_function = None
        self.reset_vertex_id()

    def isEmpty(self):
        return len(self.vertices) == 0

    def __str__(self) -> str:
        istr = "instantiatedPosOptions: " + ", ".join([str(x) for x in self.instantiatedPosOptions])
        vstr = "vertices: " + ", ".join([str(x) for x in self.vertices])
        vidstr = "vertex_id:\n" + ",\n".join([f"{x}:{self.vertex_id[x]}" for x in self.vertex_id])
        if not self.probability:
            estr = "edges: (len:{})\n".format(len(self.edges)) + ",\n".join([str(x) for x in self.edges])
            pstr = "probability: None"
        else:
            estr  = "edges: (len:{})\n".format(len(self.edges))
            estr += ",\n".join([str(x) + ", prob: {}".format(self.probability(self.vertex_id[x.start], self.vertex_id[x.end], 1)) for x in self.edges])
            for vertex, id in self.vertex_id.items():
                estr += "\n{} -> {}, prob: {}".format(vertex.optionName, vertex.optionName, self.probability(id, id, 1))
            pstr = "probability: {}".format(self.probability)
        return "\n\n".join([istr, vstr, estr, vidstr, pstr])

    def __repr__(self) -> str:
        return str(self)

    def add_vertex(self, vertex: OPFTVertex):
        self.vertices.append(vertex)
        self.alloc_vertex_id(vertex)

    def add_vertex_from_optioninfo(self, oinfo: OptionInfo):
        vertex = OPFTVertex(oinfo)
        self.add_vertex(vertex)

    def add_edge(self, edge: OPFTEdge):
        if edge.start not in self.vertices:
            self.add_vertex(edge.start)
        if edge.end not in self.vertices:
            self.add_vertex(edge.end)
        self.edges.append(edge)

    def create_complete_graph(self):
        assert len(self.edges) == 0
        assert len(self.vertex_id) == len(self.vertices)
        num = len(self.vertices)
        for i in range(num):
            for j in range(i + 1, num):
                self.add_edge(OPFTEdge(self.vertices[i], self.vertices[j]))
                self.add_edge(OPFTEdge(self.vertices[j], self.vertices[i]))

    def set_probability(self, prob_function, set_cover: list):
        self.probability = prob_function
        self.set_cover = set_cover

    def set_d_function(self, d_function):
        self.d_function = d_function

    def set_pos_options(self, posOptions):
        self.posOptions = posOptions

    def set_pos_patterns(self, posPatterns):
        self.posPatterns = posPatterns

    def set_instantiated_pos_options(self, instantiatedPosOptions):
        self.instantiatedPosOptions = instantiatedPosOptions

    def set_expected_len(self, expected_len):
        self.expected_len = expected_len
        logging.info("Set expected length: {}".format(expected_len))

    def set_attn_scores(self, attn_scores):
        self.attn_scores = attn_scores

    def alloc_vertex_id(self, vertex: OPFTVertex):
        assert vertex not in self.vertex_id
        self.vertex_id[vertex] = len(self.vertex_id)

    def reset_vertex_id(self):
        self.vertex_id = {}
        for i, vertex in enumerate(self.vertices):
            self.vertex_id[vertex] = i

    def sequence_to_optionlist(self, sequence):
        return [self.vertices[x].instantiate() for x in sequence]

    def optionlist_to_cmdline(self, option_list: "list[str]", add_pos_arg=True) -> str:
        assert option_list is not None
        assert type(option_list) == list
        cmdline_pattern = random.choice(self.posPatterns)
        # add default @OPTION
        if not "@OPTION" in cmdline_pattern:
            cmdline_pattern = "@OPTION " + cmdline_pattern
        # instantiate mapping
        placeholder_map = {}
        placeholder_map["OPTION"] = []
        # check option list is fully instantiated
        for option in option_list:
            if option.startswith("@@@"):
                option = instantiate_path("/tmp/sandbox", option, "@@@", "")
            elif option.startswith("@@$"):
                option = instantiate_path("/tmp/sandbox", option, "@@$", "")
            placeholder_map["OPTION"].append(option)
        placeholder_map["OPTION"] = " ".join(placeholder_map["OPTION"])
        for option in self.posOptions:
            assert option.name not in placeholder_map, "Positional argument is already instantiated: {}".format(option.name)
            placeholder_map[option.name] = option.instantiate() if add_pos_arg else ""
        cmdline = ""
        for item in cmdline_pattern.split():
            if item[0] == '@':
                assert item[1:] in placeholder_map, "Invalid placeholder: {}\ncmdline_pattern: {}".format(item, cmdline_pattern)
                cmdline += placeholder_map[item[1:]] + " "
            else:
                cmdline += item + " "
        return cmdline

    def __walk_with_FDProb(self, N, raw_flag=False):
        logging.info("Walking on OPFT with FDProb")
        assert self.expected_len > 0, "Expected length is not set."
        assert self.attn_scores is not None, "attn_scores is not set."
        assert self.d_function is not None, "d_function is not set."
        if raw_flag:
            result = [record_timestamp([])]
        else:
            result = [record_timestamp(self.optionlist_to_cmdline([]).split(" "))]
        seed_pool = []
        if self.isEmpty():
            for _ in range(N):
                if raw_flag:
                    result.append(record_timestamp([]))
                else:
                    result.append(record_timestamp(self.optionlist_to_cmdline([]).split(" ")))
            return result
        if N >= len(self.vertices):
            # consider all the options at the first position
            for i in range(len(self.vertices)):
                seed_pool.append([i])
                if raw_flag:
                    result.append(record_timestamp([self.vertices[i].optionName]))
                else:
                    result.append(record_timestamp(self.optionlist_to_cmdline([self.vertices[i].instantiate()]).split(" ")))
            N = N - len(self.vertices)
        if self.set_cover is not None and len(self.set_cover) > 0 and N >= len(self.set_cover):
            logging.info("Using set cover.")
            for s in self.set_cover:
                if s == "":
                    if raw_flag:
                        result.append(record_timestamp([]))
                    else:
                        result.append(record_timestamp(self.optionlist_to_cmdline([]).split(" ")))
                else:
                    index_list = [int(x) for x in s.split(',')]
                    if raw_flag:
                        result.append(record_timestamp([self.vertices[i].optionName for i in index_list]))
                    else:
                        result.append(record_timestamp(self.optionlist_to_cmdline([self.vertices[i].instantiate() for i in index_list]).split(" ")))
                N -= 1
        assert N >= 0, "Not enough chance for walking: N = {}, len(vertices) = {}, len(set_cover) = {}".format(N, len(self.vertices), len(self.set_cover))
        for _ in range(N):
            end_prob = 1 / self.expected_len
            if len(seed_pool) > 0:
                sequence = seed_pool.pop(0)
                assert len(sequence) == 1, "sequence: {}".format(sequence)
                curPos = sequence[-1]
            else:
                sequence = []
                curPos = -1
            conflict_map = [0] * len(self.vertices)
            stop_flag = False
            while True:
                if random.random() < end_prob:
                    break
                p_list = []
                if curPos == -1:
                    assert len(sequence) == 0
                for j in range(len(self.vertices)):
                    if conflict_map[j] == 1 or j in sequence:
                        p_list.append(0)
                    else:
                        # no history
                        if curPos == -1:
                            p_list.append(self.probability(0, j, 0))
                        else:
                            # attention-based probability
                            attn_p = [0] * len(sequence)
                            assert "0" in self.attn_scores, "0 not in attn_scores."
                            attn_len = len(self.attn_scores["0"])
                            assert attn_len > 1, "attn_len: {}".format(attn_len)
                            assert len(sequence) > 0, "len(sequence): {}".format(len(sequence))
                            for ik, k in enumerate(sequence):
                                if len(sequence) >= attn_len:
                                    attn_p[ik] = self.attn_scores[str(k)][str(attn_len - 1)]
                                else:
                                    attn_p[ik] = self.attn_scores[str(k)][str(len(sequence))]
                            s = sum(attn_p)
                            assert s > 0, "s: {} attn_p: {}\nsequence: {}\nattn_scores: {}".format(s, attn_p, sequence, self.attn_scores)
                            attn_p = [x / s for x in attn_p]
                            # modify the probability and exclude the existing options for each option in sequence
                            attn_v = []
                            for ik, k in enumerate(sequence):
                                _p = []
                                for _j in range(len(self.vertices)):
                                    if _j in sequence:
                                        _p.append(0)
                                    else:
                                        if self.d_function(k, _j, len(sequence)) < 0:
                                            _p.append(0)
                                        else:
                                            _p.append(self.probability(k, _j, len(sequence)))
                                s = sum(_p)
                                # If no option can increase the coverage, stop walking
                                if s == 0:
                                    stop_flag = True
                                    break
                                assert len(_p) == len(self.vertices), "len(_p): {}, len(vertices): {}".format(len(_p), len(self.vertices))
                                assert s > 0, "s: {}".format(s)
                                _new_p = [x / s for x in _p]
                                attn_v.append(_new_p[j])
                            if stop_flag:
                                break
                            assert len(attn_p) == len(attn_v), "len(attn_p): {}, len(attn_v): {}".format(len(attn_p), len(attn_v))
                            p_list.append(sum([attn_p[ik] * attn_v[ik] for ik in range(len(sequence))]))
                if stop_flag:
                    break
                # normalize p_list
                s = sum(p_list)
                if s == 0:
                    break
                p_list = [x / s for x in p_list]
                nextPos = random.choices(range(len(self.vertices)), weights=p_list)[0]
                sequence.append(nextPos)
                # update conflict_map
                for j in range(len(self.vertices)):
                    if conflict_map[j] == 1:
                        continue
                    if self.probability(nextPos, j, len(sequence)) == 0:
                        conflict_map[j] = 1
                curPos = nextPos
            if raw_flag:
                result.append(record_timestamp([self.vertices[i].optionName for i in sequence]))
            else:
                optionlist = self.sequence_to_optionlist(sequence)
                optionlist = self.optionlist_to_cmdline(optionlist).split(" ")
                result.append(record_timestamp(optionlist))
        return result

    def walk(self, N):
        from GoSe.utils.env import STRATEGY
        logging.info("Walking with strategy: {}".format(STRATEGY.name))
        if STRATEGY == Strategies.GoSe:
            return self.__walk_with_FDProb(N, raw_flag=True)
        else:
            assert False, "Unimplemented strategy: {}".format(STRATEGY.name)

    def save_probability(self, save_path):
        dir_name = os.path.dirname(save_path)
        file_name = os.path.basename(save_path)
        if not os.path.exists(dir_name):
            print("Directory {} does not exist.".format(dir_name))
            return
        if os.path.exists(save_path):
            print("File {} already exists. Will override.".format(save_path))
            os.remove(save_path)
        # save in json format
        res = dict()
        # attn_scores
        if self.attn_scores is not None:
            res['attn_scores'] = self.attn_scores
        # expected_len
        res['expected_len'] = self.expected_len
        # position_options
        res['position_options'] = [OptionInfo.to_json(x) for x in self.posOptions]
        # position_patterns
        res['position_patterns'] = [str(x) for x in self.posPatterns]
        # vertices
        res['vertices'] = [[OPFTVertex.to_json(x), self.vertex_id[x]] for x in self.vertices]
        # history_len
        res['history_len'] = self.history_len
        # prob_function
        prob_function_values = get_pmap_from_probability(self.probability, len(self.vertices), self.history_len)
        res['prob_function'] = prob_function_values
        # d_function
        d_function_values = get_pmap_from_probability(self.d_function, len(self.vertices), self.history_len)
        res['d_function'] = d_function_values
        # set_cover
        if self.set_cover is None:
            res['set_cover'] = []
        else:
            res['set_cover'] = list(self.set_cover)
        with open(save_path, 'w') as f:
            f.write(json.dumps(res, indent=4))
        print("Probability saved to {}.".format(save_path))

    def load_probability(self, load_path):
        if not os.path.exists(load_path):
            print("File {} does not exist.".format(load_path))
            return
        with open(load_path, 'r') as f:
            res = json.load(f)
        # load json
        # attn_scores
        if 'attn_scores' in res:
            self.attn_scores = res['attn_scores']
        # expected_len
        self.expected_len = res['expected_len']
        # position_options
        self.posOptions = [OptionInfo.from_json(x) for x in res['position_options']]
        self.posPatterns = [str(x) for x in res['position_patterns']]
        # self.instantiatedPosOptions = [str(x) for x in res['position_options']]
        # vertices
        vertices_json = res['vertices']
        v_cnt = len(vertices_json)
        self.vertices = [None] * v_cnt
        for v_json in vertices_json:
            v = OPFTVertex.from_json(v_json[0])
            v_id = v_json[1]
            self.vertices[v_id] = v
            self.vertex_id[v] = v_id
        # edges
        self.create_complete_graph()
        # history_len
        self.history_len = res['history_len']
        # prob_function
        prob_function_values = dict()
        prob_function_values_ = res['prob_function']
        # change all keys to int
        for i in range(v_cnt):
            prob_function_values[i] = dict()
            for j in range(v_cnt):
                prob_function_values[i][j] = dict()
                for k in range(self.history_len):
                    prob_function_values[i][j][k] = prob_function_values_[str(i)][str(j)][str(k)]
        self.probability = get_probability_from_values(prob_function_values, v_cnt, self.history_len)
        # d_function
        d_function_values = dict()
        d_function_values_ = res['d_function']
        # change all keys to int
        for i in range(v_cnt):
            d_function_values[i] = dict()
            for j in range(v_cnt):
                d_function_values[i][j] = dict()
                for k in range(self.history_len):
                    d_function_values[i][j][k] = d_function_values_[str(i)][str(j)][str(k)]
        self.d_function = get_probability_from_values(d_function_values, v_cnt, self.history_len)
        # set_cover
        if res['set_cover'] is None or len(res['set_cover']) == 0:
            self.set_cover = None
        else:
            self.set_cover = list(res['set_cover'])
        print("Probability loaded from {}.".format(load_path))