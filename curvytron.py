from __future__ import absolute_import, division, print_function

import gym
from gym import error, spaces, utils
from gym.utils import seeding

import numpy as np

import client
import time

__all__ = ['CurvytronEnv']


class State:
    def __init__(self, pixels, position, angle):
        self.angle = angle
        self.position = position
        self.pixels = pixels


class CurvytronEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, server, room, clientclass = client.CurvytronClient, **kwargs):
        self.client = clientclass(**kwargs)
        self.client.start()
        self.client.connect_to_server(server)
        time.sleep(1)
        self.client.join_room(room)

        # There's only three actions: left, right, ahead.
        self.action_space = spaces.Discrete(3)
        # Need to set shape to whatever the dimensions of the observation are.
        self.observation_space = spaces.Box(low=0, high=255, dtype=np.float32, shape=(128,128,3))
        self.action_set = {0:-1,1:0,2:1}

    def step(self, a):
        """
        Submits an action to the curvytron server and returns the state
        
        Parameters
        ----------
        
        a : int in [0, 1, 2]
            action to submit (left, straight, right)
        
        Returns
        -------
        
        state : tuple (canvas, position, angle)
            canvas (200 x 200 x 3 colour image)
            position (2D coordinate (x0, x1))
            angle (clockwise radians from 3 o'clock)
        reward : float
            0 if not done, -10 when episode ends
        done: boolean
            False until episode ends
        """
        reward = -10.0
        action = self.action_set[a]
#        observation = self.client.get_canvas()  # Or whatever the correct method is.
        done = not(self.client.player_alive and self.client.active_round)
        if not done:
            self.client.send_action(action)
            reward = 0.0

        state = State(self.client.get_canvas(), self.client.position, self.client.angle)
        return state, reward, done

    def reset(self):
        sent_ready = False
        while not (self.client.active_round and self.client.player_alive):
            if not self.client.active_game and not sent_ready:
                self.client.send_ready()
                sent_ready=True
            time.sleep(0.5)
            continue
        return State(self.client.get_canvas(), self.client.position, self.client.angle)

    def render(self, mode='human', close=False):
        pass
