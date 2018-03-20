# curvytron-client

## Install

```bash
conda create -n cc python=3 spyder
conda activate cc
pip install websockets-client
```

Connect to curvytronserver from Python using WebSocket.
Intended to be used as part of an environment for RL.

***
To see the environment drawing the players, run the following in a python script, replacing "server_address" with the actual address of your curvytron server (e.g. 127.0.0.1:8080):

```python
import env
import matplotlib.pyplot as plt
serveraddress = "127.0.0.1:8080"
environment = env.CurvytronEnv(server=serveraddress,room='room')
environment.reset()
episode_over = False
while not episode_over:
    ob,r,episode_over = environment.step(2)
    plt.imshow(ob)
    plt.pause(0.005)
print "done"
```
