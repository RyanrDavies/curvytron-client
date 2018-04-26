from __future__ import absolute_import, division, print_function
import time
import numpy as np
import random
from agent import Agent
import argparse
from heuristic_agent import (RandomAgent, HeuristicAgent1, HeuristicAgent2, 
                             RaymanAgent)

DEFAULT_ROOM = 'room_{}'.format(random.randint(0,10000))
DISPLAY_DICT = {0: '.', 1: '#'}

class MyAgent(Agent):
    """
    Your own agent. See examples given in heuristic_agent.py. In particular,
    see how to display pixels in the terminal (useful for debugging - see
    if self.display lines) and use of ray distances in RaymanAgent. There's
    no requirement to work with patches, we give this example to show a nice
    way to display pixels.
    """
    def __init__(self, name, server, room=DEFAULT_ROOM, display=True, 
                 patch_size=30, **kwargs):
        super(MyAgent, self).__init__(name, server, room, **kwargs)
        self.patch_size = patch_size
        self.display = display

    def action(self, state):
        # state.pixels is a colour image, we binarise it
        state.pixels = np.clip(
            abs(state.pixels - self.env.client.bg_color[0]).sum(axis=2),
            0,
            1
        )
        # method from agent.Agent - gets a patch around the head of the snake
        # and rotates it to be facing up (i.e. from the snake's perspective)
        patch = self.extract_patch(state, self.patch_size)
        
        # You should write some logic here - this randomly picks and action!
        choice = self.env.action_space.sample()

        # Renders the patch in the terminal
        if self.display:
            for row in patch:
                print(' '.join([DISPLAY_DICT[i] for i in row]))
            print("move: {}".format(choice))
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
    parser.add_argument('-n', '--no-opponents',
                        action='store_true',
                        default=False)
    
    args = parser.parse_args()
    serveraddress = args.serveraddress  # James' comp
#    serveraddress = "127.0.0.1:8080"  # Ryan's
#    serveraddress = "curvytron.com:80"  # Online
    room = args.room
    print(args)

    my_agent = MyAgent('MyAgent', serveraddress, room, display=True)

    if not args.no_opponents:
        opponents = [HeuristicAgent1('HeuristicAgent1', serveraddress, room),
                     HeuristicAgent2('HeuristicAgent2', serveraddress, room),
                     RaymanAgent('RaymanAgent', serveraddress, room),
                     RandomAgent('RandomAgent',  serveraddress, room)]
        my_agent.start()
        for op in opponents:
            op.start()
    else:   
        my_agent.start()
    while True:
        time.sleep(1)
