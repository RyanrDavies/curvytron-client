# curvytron-client

Connect to curvytronserver from Python using WebSocket.
Intended to be used as part of an environment for RL.

***

### Not Finished.

* Need to write the parser for the messages received during the game.
* May want to reconsider the way messages are treated -- received messages are
more like a list of messages.
* Look at Pillow's ImageDraw module for the graphics
* Restructure join game method -- some of this can be left to the general message parser.
For example, all room:join messages need to be parsed so that we know what color each player is, so instead of waiting for the reply to find our ID, can just pick that up in the loop.