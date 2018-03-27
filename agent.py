from __future__ import absolute_import, division, print_function

import math
import random
import threading

import numpy as np
from skimage.transform import rotate

from env import CurvytronEnv


class Agent(threading.Thread):
    def __init__(self, name, server, room, **kwargs):
        super(Agent, self).__init__()

        self.env = CurvytronEnv(server, room,
                                name=name, color="#%06x" % random.randint(0, 0xFFFFFF),
                                **kwargs)

    def run(self):
        while True:
            state = self.env.reset()
            episode_over = False
            while not episode_over:
                action = self.action(state)
                state, reward, episode_over = self.env.step(action)

    def extract_patch(self, state, s=30):
        # TODO: test/fix
        sz = s // 2
        x, y = state.position
        x = int(x) + sz + 1
        y = int(y) + sz + 1

        angle = math.degrees(state.angle) + 90 # This is clockwise angle from 12 o'clock
        pixels = state.pixels
        expanded = np.ones([pixels.shape[0] + s+2, pixels.shape[1] + s+2])
        assert expanded.shape[0] == expanded.shape[1], "Expanded Shape={}".format(expanded.shape)
        expanded[(sz+1):-(sz+1), (sz+1):-(sz+1)] = pixels
        clipped = expanded[(x - sz):(x + sz), (y - sz):(y + sz)]
        assert ((x+sz)-(x-sz)) == ((y+sz)-(y-sz))
        assert clipped.shape[0] == clipped.shape[1], "Clipped Shape={}".format(clipped.shape)
        # rotate expects angle to be anti-clockwise from 12
        rot = rotate(clipped, angle=angle)

        return rot > 0

    def action(self, state):
        raise NotImplementedError()