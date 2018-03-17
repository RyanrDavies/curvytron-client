import gym
from gym import error, spaces, utils
from gym.utils import seeding

import numpy as np

from client import CurvytronClient


class CurvytronEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, server, room, **kwargs):
        self.client = CurvytronClient(server, **kwargs)
        self.client.start()
        self.client.join_room(room)

        # There's only three actions: left, right, ahead.
        self.action_space = spaces.Discrete(3)
        # Need to set shape to whatever the dimensions of the observation are.
        self.observation_space = spaces.Box(low=0, high=255, dtype=np.float32, shape=(128,128,3))
        self.action_set = {0:-1,1:0,2:1}

    def step(self, a):
        reward = 0.0

        action = self.action_set[a]
        self.client.send_action(action)

        observation = self.client.get_canvas()  # Or whatever the correct method is.

        return observation, reward, self.client.player_alive and self.client.active_round

    def reset(self):
        if not self.client.active_game:
            self.client.send_ready()
        while not self.client.active_round:
            continue

    def render(self, mode='human', close=False):
        pass
