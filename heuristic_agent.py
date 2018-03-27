from __future__ import absolute_import, division, print_function

import time
import numpy as np

import random

from agent import Agent

# serveraddress = "129.215.91.49:8080"
# serveraddress = "www.curvytron.com:80"
serveraddress = "127.0.0.1:8080"

room = 'room_{}'.format(random.randint(0,10000))

DISPLAY_DICT = {0: '.', 1: '#'}


class RandomAgent(Agent):
    def __init__(self, name, **kwargs):
        super(RandomAgent, self).__init__(name, serveraddress, room, **kwargs)

    def action(self, _):
        return self.env.action_space.sample()


class HeuristicAgent(Agent):
    def __init__(self, name, patch_size=50, display=False, **kwargs):
        super(HeuristicAgent, self).__init__(name, serveraddress, room, **kwargs)
        self.patch_size = patch_size
        sz = patch_size//2
        # Precomputed distances
        self.sq_dist = np.arange(sz) ** 2 + np.arange(sz -2)[:, np.newaxis] ** 2
        self.display = display

    def action(self, state):
        patch = self.extract_patch(state, self.patch_size)
        assert patch.shape[0] == self.patch_size, "Shape={}".format(patch.shape)
        assert patch.shape[1] == self.patch_size, "Shape={}".format(patch.shape)
        sz = self.patch_size//2
        left, right = patch[:sz -2, :sz], patch[:sz -2, sz:]
        left[0, 0] = right[0, -1] = 1  # hack to handle empty box
        left_dist = self.sq_dist[::-1, ::-1] * left
        right_dist = self.sq_dist[::-1, :] * right
        closest_left = np.min(left_dist[left_dist > 0])
        closest_right = np.min(right_dist[right_dist > 0])

        if closest_left < closest_right:
            choice = 2  # Right
        elif closest_right < closest_left:
            choice = 0  # Left
        else:
            choice = 1  # Straight

        if self.display:  # and closest_right == closest_left == 1:
            for row in patch:
                print(''.join([DISPLAY_DICT[i] for i in row]))
            print("left: {} || right: {} || move: {}".format(closest_left,closest_right,choice))
            print("\033[{}A".format(self.patch_size+1), end='\r')
        return choice


if __name__ == '__main__':
    print('server: {} room: room_{}'.format(serveraddress, room))

    agent = HeuristicAgent('AvidLearner', display=True)
    opponents = [HeuristicAgent('AngryOpponent1'),
                 HeuristicAgent('AngryOpponent2')]

    agent.start()
    for op in opponents:
        op.start()

    while True:
        time.sleep(1)
