from __future__ import absolute_import, division, print_function
import time
import numpy as np
import random
from agent import Agent
import argparse

__all__ = ['RandomAgent', 'HeuristicAgent1', 'HeuristicAgent2', 'RaymanAgent']

DEFAULT_ROOM = 'room_{}'.format(random.randint(0,10000))
DISPLAY_DICT = {0: '.', 1: '#'}
DIRECTION = {
    'N':  np.array((-1, 0)),
    'NE': np.array((-1, 1)),
    'E':  np.array(( 0, 1)),
    'SE': np.array(( 1, 1)),
    'S':  np.array(( 1, 0)),
    'SW': np.array(( 1,-1)),
    'W':  np.array(( 0,-1)),
    'NW': np.array((-1,-1))
}

         
def is_blocked(patch):
    """
    Returns true if there are two on pixels directly ahead
    """
    sz = patch.shape[0] // 2  # Assumes patch size even
    blocked = False
    for row in range(sz-2, -1, -1):  # Scan from center of patch to top
        if patch[row, sz] == 1 and patch[row, sz-1] == 1:
            blocked = True
            break
    return blocked


def configure_compass_rays(patch_size):
    if patch_size & 1:  # if patch size is odd
        idx = (patch_size-1) // 2
        start = np.array(((idx,idx),) * 8)
        direc = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        directions = [DIRECTION[dd] for dd in direc]
        ray_conf = dict(zip(direc, zip(start, directions)))
    else:
        raise NotImplementedError('Not implemented for even patch size')
#        idx = (patch_size) // 2
#        start = ((idx,idx),) * 8
#        # Naming example: cNW_N = *central* North West pixel to North pixel
#        names = ['cNW_N', 'cNE_N',
#                 'cNW_NE', 'cNE_NE', 'cSE_NW',
#                 'cNE_E', 'cSE_E'
#                 ]
#        direc = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NE']
#        directions = [DIRECTION[dd] for dd in direc]
#        ray_conf = dict(zip(direc, zip(start, directions)))
    return ray_conf


def get_ray_lengths(patch, ray_conf=None, start_allowance=1, max_len=100):
    """
    Returns the length of a continous string of zeros along the defined rays.
    By default, the rays are defined as starting at the centre and pointing 
    in the direction of compass points N, NE, E, ..., W, NW. To avoid issues 
    with the center being non-zero, `start_allowance` is the maximum number of
    non-zero squares allowed from the centre before starting the count.
    
    N.B. this will break if the obbstructing line is only 1 pix thick and going
    perpendicular to a diagonal ray (the ray will think it can pass straight
    through)
    """
    if ray_conf is None:
        ray_conf = configure_compass_rays(patch.shape[0])
    ray_len = {}
    for ray_id, (start, direc) in ray_conf.items():
        this_ray_len = 0
        for ii in range(max_len):
            idx = start + ii*direc
            if min(idx) < 0 or max(idx) >= patch.shape[0]:
                break
            if patch[idx[0], idx[1]] == 0:
                this_ray_len += 1
            else:
                if ii+1 <= start_allowance:
                    # Simply restart the count and don't break
                    this_ray_len = 0
                else:
                    break
        ray_len[ray_id] = this_ray_len
    return ray_len


class RandomAgent(Agent):
    def __init__(self, name, server, room=DEFAULT_ROOM, **kwargs):
        super(RandomAgent, self).__init__(name, server, room, **kwargs)

    def action(self, _):
        return self.env.action_space.sample()


class HeuristicAgent1(Agent):
    def __init__(self, name, server, room=DEFAULT_ROOM, patch_size=50, 
                 display=False, **kwargs):
        super(HeuristicAgent1, self).__init__(name, server, room, 
                                             **kwargs)
        assert patch_size // 2 == patch_size / 2, "Patch size must be even"
        self.patch_size = patch_size
        sz = patch_size//2
        # Precomputed distances
        self.sq_dist = np.arange(sz) ** 2 + np.arange(sz -2)[:, np.newaxis] ** 2
        self.display = display

    def action(self, state):
        state.pixels = np.clip(abs(state.pixels - self.env.client.bg_color[0]).sum(axis=2),0,1)
        patch = self.extract_patch(state, self.patch_size)
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
                print(' '.join([DISPLAY_DICT[i] for i in row]))
            print("left: {} || right: {} || move: {}".format(closest_left,closest_right,choice))
            print("\033[{}A".format(self.patch_size+1), end='\r')
        
        return choice


class HeuristicAgent2(Agent):
    """
    Same as HeuristicAgent1 but will turn if there's a blockage ahead which
    is the same distance from the left and right e.g. HeuristicAgent1 will 
    carry on straight if it is headed at a wall dead on, HeuristicAgent2 will
    pick a direction randomly.
    """
    def __init__(self, name, server, room=DEFAULT_ROOM, patch_size=50, 
                 display=False, **kwargs):
        super(HeuristicAgent2, self).__init__(name, server, room, 
                                             **kwargs)
        assert patch_size // 2 == patch_size / 2, "Patch size must be even"
        self.patch_size = patch_size
        sz = patch_size//2
        # Precomputed distances
        self.sq_dist = np.arange(sz) ** 2 + np.arange(sz -2)[:, np.newaxis] ** 2
        self.display = display
        
    
    def action(self, state):
        state.pixels = np.clip(abs(state.pixels - self.env.client.bg_color[0]).sum(axis=2), 0, 1)
        patch = self.extract_patch(state=state, patch_size=self.patch_size)
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
            if is_blocked(patch):
                choice = 2  # Right
            else:
                choice = 1  # Straight
            
        if self.display:  # and closest_right == closest_left == 1:
            for row in patch:
                print(' '.join([DISPLAY_DICT[i] for i in row]))
            print("left: {} || right: {} || move: {}".format(closest_left,closest_right,choice))
            print("pos: {} || angle: {}".format(state.position, state.angle))
            print("\033[{}A".format(self.patch_size+2), end='\r')
        
#        if self.display:  # and closest_right == closest_left == 1:
#            for row in state.pixels:
#                print(' '.join([DISPLAY_DICT[i] for i in row]))
#            print("left: {} || right: {} || move: {}".format(closest_left,closest_right,choice))
#            print("\033[{}A".format(state.pixels.shape[0]+1), end='\r')
        return choice


class RaymanAgent(Agent):
    def __init__(self, name, server, room=DEFAULT_ROOM, patch_size=75,
                 turning_distance=60, display=False, **kwargs):
        super(RaymanAgent, self).__init__(name, server, room, **kwargs)
        assert patch_size // 2 != patch_size / 2, "Patch size must be odd"
        self.patch_size = patch_size
        self.turning_distance = turning_distance
        self.display = display
        self.ray_conf = configure_compass_rays(patch_size)
    
    def run(self):
        while True:
            state = self.env.reset()
            episode_over = False
            action = 1
            while not episode_over:
                action = self.action(state, action)
                state, reward, episode_over = self.env.step(action)
    
    def action(self, state, curr_action):
        state.pixels = np.clip(abs(state.pixels - self.env.client.bg_color[0]).sum(axis=2), 0, 1)
        patch = self.extract_patch(state, self.patch_size)
        ray_len = get_ray_lengths(patch, ray_conf=self.ray_conf, 
                                  start_allowance=2, max_len=self.patch_size)
        
        if ray_len['N'] <= self.turning_distance:  # Something is ahead
            if ray_len['NW'] == ray_len['NE']:
                if ray_len['SW'] == ray_len['SE']:
                    if curr_action == 1:
                        choice = 0  # Arbitrary
                    else:
                        choice = curr_action  # keep going same way
                elif ray_len['SW'] > ray_len['SE']:
                    choice = 0
                else:
                    choice = 2
            elif ray_len['NW'] > ray_len['NE']:
                choice = 0
            else:
                choice = 2
        else:  # Nothing ahead
            choice = 1
            
        if self.display:  # and closest_right == closest_left == 1:
            for row in patch:
                print(' '.join([DISPLAY_DICT[i] for i in row]))
            print("rays: {} || move: {}".format(ray_len, choice))
            print("\033[{}A".format(self.patch_size+1), end='\r')
        return choice


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--serveraddress', 
                        help="The address of the server to connect to",
                        default='129.215.91.49:8080')
    parser.add_argument('-r', '--room', 
                        help="The name of the room to join",
                        default=DEFAULT_ROOM)
    args = parser.parse_args()
    serveraddress = args.serveraddress  # James' comp
#    serveraddress = "127.0.0.1:8080"  # Ryan's
#    serveraddress = "curvytron.com:80"  # Online
    room = args.room
    
    print('server: {} room: {}'.format(serveraddress, room))

    agent = RaymanAgent('Rayman', serveraddress, room, display=True)
#    agent = RaymanAgent('RaymanAgent', server=serveraddress, room=room, 
#                           display=True)
    opponents = [HeuristicAgent1('HeuristicAgent1', serveraddress, room),
                 HeuristicAgent2('HeuristicAgent2', serveraddress, room)]

    agent.start()
    for op in opponents:
        op.start()

    while True:
        time.sleep(1)
