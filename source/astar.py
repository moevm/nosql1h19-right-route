# -*- coding: utf-8 -*-
""" generic A-Star path searching algorithm """

""" Modification """

from abc import ABCMeta, abstractmethod
from heapq import heappush, heappop


__author__ = "Julien Rialland"
__copyright__ = "Copyright 2012-2017, J.Rialland"
__license__ = "BSD"
__version__ = "0.9"
__maintainer__ = __author__
__email__ = "julien.rialland@gmail.com"
__status__ = "Production"

Infinite = float('inf')


class AStar:
    __metaclass__ = ABCMeta
    __slots__ = ()

    class SearchNode:
        __slots__ = ('data', 'gscore', 'fscore',
                     'closed', 'came_from', 'out_openset')

        def __init__(self, data, gscore=Infinite, fscore=Infinite):
            self.data = data
            self.gscore = gscore
            self.fscore = fscore
            self.closed = False
            self.out_openset = True
            self.came_from = None

        def __lt__(self, b):
            return self.fscore < b.fscore

    class SearchNodeDict(dict):

        def __missing__(self, k):
            v = AStar.SearchNode(k)
            self.__setitem__(k, v)
            return v

    @abstractmethod
    def heuristic_cost_estimate(self, current, goal):
        """Computes the estimated (rough) distance between a node and the goal, this method must be implemented in a subclass. The second parameter is always the goal."""
        raise NotImplementedError

    @abstractmethod
    def distance_between(self, n1, n2):
        """Gives the real distance between two adjacent nodes n1 and n2 (i.e n2 belongs to the list of n1's neighbors).
           n2 is guaranteed to belong to the list returned by the call to neighbors(n1).
           This method must be implemented in a subclass."""
        raise NotImplementedError

    @abstractmethod
    def neighbors(self, node):
        """For a given node, returns (or yields) the list of its neighbors. this method must be implemented in a subclass"""
        raise NotImplementedError

    def is_goal_reached(self, current, goal):
        """ returns true when we can consider that 'current' is the goal"""
        return current == goal

    def reconstruct_path(self, last, reversePath=False):
        def _gen():
            current = last
            while current:
                yield current.data
                current = current.came_from

        if reversePath:
            return _gen()
        else:
            return reversed(list(_gen()))

    def astar(self, start, goal, nodes_client_for_left=None, reversePath=False):
        if self.is_goal_reached(start, goal):
            return [start]
        searchNodes = AStar.SearchNodeDict()
        startNode = searchNodes[start] = AStar.SearchNode(
            start, gscore=.0, fscore=self.heuristic_cost_estimate(start, goal))
        openSet = []
        heappush(openSet, startNode)

        while openSet:
            current = heappop(openSet)
            if self.is_goal_reached(current.data, goal):
                return self.reconstruct_path(current, reversePath)
            current.out_openset = True
            current.closed = True

            cur, prev = None, None
            # если учёт левых поворотов - учёт предыдущего шага
            if nodes_client_for_left:
                cur = nodes_client_for_left.find_one({'_id': current.data}, {'loc': 1})
                prev = cur
                if current.came_from:
                    prev = nodes_client_for_left.find_one({'_id': current.came_from.data}, {'loc': 1})

            for neighbor in [searchNodes[n] for n in self.neighbors(current.data)]:
                if neighbor.closed:
                    continue

                # поиск поворотов налево/разворотов
                if nodes_client_for_left:
                    new = nodes_client_for_left.find_one({'_id': neighbor.data}, {'loc': 1})
                    prev_vector = [cur['loc'][1] - prev['loc'][1], cur['loc'][0] - prev['loc'][0]]
                    tmp_vector = [new['loc'][1] - prev['loc'][1], new['loc'][0] - prev['loc'][0]]
                    new_vector = [new['loc'][1] - cur['loc'][1], new['loc'][0] - cur['loc'][0]]

                    import numpy as np

                    cos = 1
                    if current.came_from:
                        cos = np.dot(prev_vector, new_vector) / (np.linalg.norm(prev_vector) * np.linalg.norm(new_vector))
                        cos = np.clip(cos, -1, 1)  # угол между векторами движения
                    ang = np.degrees(np.arccos(np.clip(cos, -1, 1)))
                    tmp = float(np.cross(prev_vector, tmp_vector))  # для определения с какой стороны точка
                    if tmp > 0:
                        # новая точка слева от вектора движения
                        # fixme критерии не идеальны
                        if 45.0 <= ang < 140.0:     # левый поворот
                            continue
                        if 140.0 <= ang <= 180.0:       # разворот
                            continue

                tentative_gscore = current.gscore + self.distance_between(current.data, neighbor.data)
                if tentative_gscore >= neighbor.gscore:
                    continue
                neighbor.came_from = current
                neighbor.gscore = tentative_gscore
                neighbor.fscore = tentative_gscore + self.heuristic_cost_estimate(neighbor.data, goal)
                if neighbor.out_openset:
                    neighbor.out_openset = False
                    heappush(openSet, neighbor)
        return None


def find_path(start, goal, neighbors_fnct, reversePath=False, heuristic_cost_estimate_fnct=lambda a, b: Infinite,
              distance_between_fnct=lambda a, b: 1.0, is_goal_reached_fnct=lambda a, b: a == b):
    """A non-class version of the path finding algorithm"""

    class FindPath(AStar):
        def heuristic_cost_estimate(self, current, goal):
            return heuristic_cost_estimate_fnct(current, goal)

        def distance_between(self, n1, n2):
            return distance_between_fnct(n1, n2)

        def neighbors(self, node):
            return neighbors_fnct(node)

        def is_goal_reached(self, current, goal):
            return is_goal_reached_fnct(current, goal)

    return FindPath().astar(start, goal, reversePath)


__all__ = ['AStar', 'find_path']
