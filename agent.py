from __future__ import absolute_import, division, print_function

import math
import random
import threading
from skimage.transform import rotate
from skimage.util import pad

from curvytron import CurvytronEnv


class Agent(threading.Thread):
    def __init__(self, name, server, room, **kwargs):
        super(Agent, self).__init__()
        self.env = CurvytronEnv(server, room, name=name, 
                                color="#%06x" % random.randint(0, 0xFFFFFF),
                                **kwargs)

    def run(self):
        while True:
            state = self.env.reset()
            episode_over = False
            while not episode_over:
                action = self.action(state)
                state, reward, episode_over = self.env.step(action)

    def extract_patch(self, state, patch_size=30, thresh=0.1):
        """
        If patch_size is even, define 'central' position of the patch to be the
        south west square and get i.e. for patch of size (10, 10) state.pos 
        will be at point (5, 4). If s is even, there is a central square e.g.
        for patch size 11 state.pos will be at (5, 5).
        
        Rotate the canvas first. This is because if you take the patch then
        rotate this patch to the angle of the player, zeros are used to fill 
        the patch.
        """
        hps = patch_size//2  # floor(half_patch_size)
        x0, x1 = [int(xx) for xx in state.position]
        # The angle of the agent clockwise from 12 o'clock
        angle = math.degrees(state.angle) + 90
        # rotate's angle argument is how many degrees to rotate *anticlockwise*
        # Additionally, the coordinates are reversed in skimage
        ### pixels is the game board oriented in the direction of the agent ###
        pixels = pad(state.pixels.astype('float'), hps+1, 
                     mode='constant', constant_values=1)
        # Because of padding x0 <- x0 + hps + 1
        x0, x1 = x0+hps+1, x1+hps+1
        pixels_rot = rotate(image=pixels, angle=angle,
                            center=(x1, x0))
        # Padding with zeros to account for selection near the edges
        if patch_size & 1:  # if patch size is odd
            patch = pixels_rot[(x0-hps):(x0+hps+1), (x1-hps):(x1+hps+1)]
        else:
            # Put resulting centre to be in the SW central square
            patch = pixels_rot[(x0-hps):(x0+hps), (x1-hps+1):(x1+hps+1)]
        return patch > thresh

    def action(self, state):
        raise NotImplementedError()