
class Weight:
    def __init__(self):
        # the number of nodes created from that node
        self.successors = 0

        # the number of times this node or any successor nodes fail
        # every single try at code will lead to one failure and a failed node will lead to four
        self.failures = 0

        # the furthest path from primitive to node upon its creation
        self.depth = 0

    def calculate_weight(self, trials):
        if self.depth == 0:
            return 0
        answer = ((self.successors + trials)/(self.depth + (self.failures/2)))
        return answer