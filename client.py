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

    def __init__(self, server, name='pythonClient', color="#ffffff", room=''):
        super(CurvytronClient, self).__init__()

        self.message_id = -1

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

    def run(self):
        self.ws.settimeout(0.05)
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

    def _recv_message(self,timeout=None,default=None):
        if timeout:
            prev_timeout = self.ws.gettimeout()
            self.ws.settimeout(timeout)
            try:
                message = json.loads(self.ws.recv())
            except websocket.WebSocketTimeoutException:
                message=default
            finally:
                self.ws.settimeout(prev_timeout)
        else:
            message = json.loads(self.ws.recv())
        return message

    def _wait_for_message(self,message_type=None,**kwargs):
        message =  self._recv_message(**kwargs)
        if kwargs.has_key('default') and message == kwargs['default']:
            return message
        if message_type == message[0][0]:
            return message
        else:
            self._parse_message(message)
            return self._wait_for_message(message_type,**kwargs)

    def _wait_for_reply(self,**kwargs):
        message =  self._recv_message(**kwargs)
        if kwargs.has_key('default') and message == kwargs['default']:
            return message
        if message[0][0] == self.message_id:
            return message
        else:
            self._parse_message(message)
            return self._wait_for_reply(**kwargs)

    def _join_room(self, target_room):
        """Doc string
        If the provided room exists, join it.
        Otherwise, create and configure the room,
        and then join it.
        :param target_room:
        :return:
        """

        self._send_message(self.FETCH_ROOMS, {})
        rooms = self._wait_for_message("room:open",timeout=1,default=[])
        for room in rooms:
            if room[1]['name'] == target_room:
                break
        else:
            # create room
            self._send_message(self.MAKE_ROOM, {'room_name': target_room})
            response = self._wait_for_reply()
            assert(response[0][1]['success'])

        # join room
        self._send_message(self.JOIN_ROOM, {'room_name': target_room})
        response = self._wait_for_reply()
        assert(response[0][1]['success'])
        self._send_message(self.ADD_PLAYER, {})
        response = self._wait_for_reply()
        print "recevied message", response
        assert (response[0][1]['success'])
        response = self._wait_for_message('room:join')
        if (response[0][0] == 'room:join' and response[0][1]['player']['client'] == self.client_id
                and response[0][1]['player']['name'] == self.name):
            self.player_id = response[0][1]['player']['id']

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
