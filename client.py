import websocket
import json
import threading

websocket.enableTrace(False)


class CurvytronClient(threading.Thread):

    FETCH_ROOMS = '[["room:fetch"]]'
    WHOAMI = '[["whoami",null,0]]'
    MAKE_ROOM = '[["room:create",{{"name":"{room_name}"}},{msg_id}]]'
    PLAYER_MOVE = '[["player:move",{{"avatar":{player_id},"move":{action}}}]]'
    JOIN_ROOM = '[["room:join",{{"name":"{room_name}","password":null}},{msg_id}]]'
    ADD_PLAYER = '[["player:add",{{"name":"{player_name}","color":"{player_color}"}},{msg_id}]]'

    def __init__(self, server, name='pythonClient', color="#ffffff"):
        super(CurvytronClient, self).__init__()

        self.message_id = -1

        self.ws = websocket.WebSocket()
        self.alive = threading.Event()
        self.alive.set()

        self.name = name
        self.color = color
        self.game_state = None
        self.active_game = False
        self.server = {'address': server, 'rooms': []}
        self.game = {'players': {}}
        self.message_responses = {}

        self.client_id = None
        self.player_id = None
        self._connect_to_server(server=server)
        # self._join_room(room)

    def run(self):
        self.ws.settimeout(0.05)
        while self.alive.isSet():
            try:
                recvd = self.ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            # if message[:2] == '[[':
            self._process_recvd(recvd)

    def join(self, timeout=None):
        self.alive.clear()
        self.ws.close()
        super(CurvytronClient, self).join(timeout)

    def _process_recvd(self, recvd):
        messages = json.loads(recvd)
        for message in messages:
            self._parse_message(message)

    def _parse_message(self, message):

        if message[0] == 'position':
            pos = (message[1][1], message[1][2])
            if self.game['players'][message[1][0]]['printing']:
                self.game['trails'][message[1][0]].append(pos)
            self.game['players'][message[1][0]]['position'] = pos

        elif message[0] == 'angle':
            self.game['players'][message[1][0]]['angle'] = message[1][1]

        elif message[0] == 'property':
            self.game['players'][message[1][0]][message[1][1]] = message[1][2]

        elif message[0] == "game:start":
            self.active_game = True

        elif message[0] == "game:stop":
            self.active_game = False

        elif message[0] == "round:new":
            pass  # self.active_game = False

        elif message[0] == "round:end":
            pass  # self.active_game = False

        elif message[0] == 'room:join':
            player_details = message[1]['player']
            self.game['players'][player_details['id']] = {'name': player_details['name'],
                                                          'color': player_details['color'],
                                                          'printing': False}
            if player_details['name'] == self.name and player_details['client'] == self.client_id:
                self.player_id = player_details['id']

        elif message[0] == 'room:open':
            self.server['rooms'].append(message[1])

        elif isinstance(message[0], int):
            self.message_responses[message[0]] = message[1]

        else:
            pass

    def _connect_to_server(self, server):
        """
        Connect to  the provided server and request client ID.
        :param server:
        :return:
        """
        self.ws.connect('ws://%s' % server)
        self._send_message(self.WHOAMI, {})
        response = self._recv_message()
        self.client_id = int(response[0][1])
        self._send_message(self.FETCH_ROOMS, {})

    def _recv_message(self, timeout=None, default=None):
        if timeout:
            prev_timeout = self.ws.gettimeout()
            self.ws.settimeout(timeout)
            try:
                message = json.loads(self.ws.recv())
            except websocket.WebSocketTimeoutException:
                message = default
            finally:
                self.ws.settimeout(prev_timeout)
        else:
            message = json.loads(self.ws.recv())
        return message

    def _wait_for_reply(self, message_id):
        while message_id not in self.message_responses:
            continue

    def join_room(self, target_room):
        """Doc string
        If the provided room exists, join it.
        Otherwise, create and configure the room,
        and then join it.
        :param target_room:
        :return:
        """

        for room in self.server.get('rooms', []):
            if room[1]['name'] == target_room:
                break
        else:
            # create room
            self._send_message(self.MAKE_ROOM, {'room_name': target_room})
            self._wait_for_reply(self.message_id)
            assert(self.message_responses[self.message_id]['success'])
            # TODO: Turn off bonuses

        # join room
        self._send_message(self.JOIN_ROOM, {'room_name': target_room})
        self._wait_for_reply(self.message_id)
        assert (self.message_responses[self.message_id]['success'])
        self._send_message(self.ADD_PLAYER, {})
        self._wait_for_reply(self.message_id)
        assert (self.message_responses[self.message_id]['success'])

    def _send_message(self, message, message_args):
        """
        Send a message to the server, substituting values
        in message_args dict for placeholders.
        :param message:
        :param message_args:
        :return:
        """
        self.message_id += 1
        self.ws.send(message.format(msg_id=self.message_id, client_id=self.client_id, player_id=self.player_id,
                                    player_name=self.name, player_color=self.color, **message_args))

    def send_action(self, action):
        self._send_message(self.PLAYER_MOVE, {'action': action})
