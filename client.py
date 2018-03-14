import websocket
import json
import threading


class CurvytronClient(threading.Thread):

    FETCH_ROOMS = '[[room:fetch]]'
    WHOAMI = '[["whoami",null,0]]'
    MAKE_ROOM = '[["room:create",{{"name":"{name}"}},{msg_id}]]'
    PLAYER_MOVE = '[["player:move",{{"avatar":{player_id},"move":{action}}}]]'

    def __init__(self, server, name='pythonClient', color="#ffffff", room=None):
        super(CurvytronClient, self).__init__()

        self.ws = websocket.WebSocket()
        self.alive = threading.Event()
        self.alive.set()

        self.name = name
        self.color = color
        self.game_state = None
        self.active_game = False

        self.client_id = None
        self.player_id = None
        self._connect_to_server(server=server)
        self._join_room(room)
        self.message_id = 0
        self.ws.settimeout(0.05)

    def run(self):
        while self.alive.isSet():
            try:
                message = self.ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            if message[:2] == '[[':
                self._parse_message(message)

    def join(self, timeout=None):
        self.alive.clear()
        self.ws.close()
        super(CurvytronClient, self).join(timeout)

    def _parse_message(self, message):
        pass

    def _connect_to_server(self, server):
        """
        Connect to  the provided server and request client ID.
        :param server:
        :return:
        """
        self.ws.connect('ws://%s' % server)
        self._send_message(self.WHOAMI, {})
        response = self.ws.recv()
        self.client_id = int(response.split(',')[-1][:-2])

    def _join_room(self, target_room):
        """Doc string
        If the provided room exists, join it.
        Otherwise, create and configure the room,
        and then join it.
        :param target_room:
        :return:
        """

        self._send_message(self.FETCH_ROOMS, {})
        rooms = self.ws.recv()
        rooms = json.loads(rooms)
        for room in rooms:
            if room[1]['name'] == target_room:
                break
        else:
            # create room
            pass

        # join room
        self.player_id = None
        pass

    def _send_message(self, message, message_args):
        """
        Send a message to the server, substituting values
        in message_args dict for placeholders.
        :param message:
        :param message_args:
        :return:
        """
        self.ws.send(message.format(msg_id=self.message_id, client_id=self.client_id, player_id=self.player_id,
                                    name=self.name, **message_args))

    def send_action(self, action):
        self._send_message(self.PLAYER_MOVE, {'action': action})
