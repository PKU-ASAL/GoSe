from GoSe.graph.opft_vertex import OPFTVertex

class OPFTEdge:
    def __init__(self, start: OPFTVertex, end: OPFTVertex, attributes=[]):
        self.start = start
        self.end = end
        self.attributes = attributes
    
    def __str__(self) -> str:
        return f"  {self.start.optionName} -> {self.end.optionName}, attributes={self.attributes})"

    def __repr__(self) -> str:
        return str(self)
