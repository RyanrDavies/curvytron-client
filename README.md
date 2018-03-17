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
Client is now "minimally working". It can connect to a server, join a room and parse the gameplay information into its attributes. The message receiving is not very robust though.

To see the client storing the positions of the players, run the following in an interactive session, replacing "server_address" with the actual address of your curvytron server (e.g. 127.0.0.1:8080):

```python
pyclient = client.CurvytronClient(server='server_address')
pyclient.start()
pyclient.join_room('room')
```
Join the room as another player using your browser, but don't mark this user as ready yet. Then:
```python
pyclient.send_ready()
while True:                                                           
    s = []
    players = pyclient.game['players'].keys()
    for p in players:
        s.append(pyclient.game['players'][p]['name'])
        s.append(' : ')
        s.append(str(pyclient.game['players'][p].get('position','')))
        s.append(' | ')
         print ''.join(s)
```
In your browser, mark the other user as ready. Once the game starts, the positions of the players should be benig printed in your interactive session.
***

### Not Finished.

* May want to expand the parser for the messages
* Think about the way game/ player information is seperated when being stored
* Need to decide how to handle reset function of environment and implement any needed status tracking in the client.
    * Reset function will probably just block until the client says it's in an active round. Will need to check the game is active, send ready signal if not.
* Look at Pillow's ImageDraw module for the graphics