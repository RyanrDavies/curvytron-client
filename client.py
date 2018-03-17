import websocket
import json
import threading
from collections import defaultdict

websocket.enableTrace(False)

class CurvytronClient(threading.Thread):
    BONUS_NAMES = [
        'BonusSelfSmall',
        'BonusSelfSlow',
        'BonusSelfFast',
        'BonusSelfMaster',
        'BonusEnemySlow',
        'BonusEnemyFast',
        'BonusEnemyBig',
        'BonusEnemyInverse',
        'BonusEnemyStraightAngle',
        'BonusGameBorderless',
        'BonusAllColor',
        'BonusGameClear'
    ]
    FETCH_ROOMS = '[["room:fetch"]]'
    WHOAMI = '[["whoami",null,0]]'
    MAKE_ROOM = '[["room:create",{{"name":"{room_name}"}},{msg_id}]]'
    PLAYER_MOVE = '[["player:move",{{"avatar":{player_id},"move":{action}}}]]'
    JOIN_ROOM = '[["room:join",{{"name":"{room_name}","password":null}},{msg_id}]]'
    ADD_PLAYER = '[["player:add",{{"name":"{player_name}","color":"{player_color}"}},{msg_id}]]'
    READY = '[["ready"]]'
    PLAYER_READY = '[["room:ready", {{"player": {player_id}}}, {msg_id}]]'
    BONUS_CHANGE_ROOM = '[["room:config:bonus",{{"bonus":"{bonus_name}","enabled":{enabled}}}, {msg_id}]]'
    
    def __init__(self, server, name='pythonClient', color="#ffffff", verbose=False):
        super(CurvytronClient, self).__init__()

        self.message_id = -1

        self.ws = websocket.WebSocket()
        self.alive = threading.Event()
        self.alive.set()
        self.verbose = verbose

        self.name = name
        self.color = color
        self.game_state = None
        self.active_game = False
        self.server = {'address': server, 'rooms': []}
        self.game = {'players': {}, 'trails': defaultdict(list)}
        self.message_responses = {}
        self.player_alive = True
        self.round_score = 0

        self.client_id = None
        self.player_id = None
        self._connect_to_server(server=server)

    def run(self):
        self.ws.settimeout(0.05)
        while self.alive.isSet():
            try:
                recvd = self.ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            self._process_recvd(recvd)

    def join(self, timeout=None):
        self.alive.clear()
        self.ws.close()
        super(CurvytronClient, self).join(timeout)

    def create_room(self, target_room=None):
        """Create room called target_room with bonuses listed in bonuses
        """
        for room in self.server.get('rooms', []):
            assert room['name'] != target_room, "Room already exists"
        self._send_message(self.MAKE_ROOM, {'room_name': target_room})
        self._wait_for_reply(self.message_id)
        assert(self.message_responses[self.message_id]['success'])
        
    def set_bonuses(self, target_room=None, on_bonuses=None):
        BONUS_NAMES = self.BONUS_NAMES
        if on_bonuses is None:
            off_bonuses = BONUS_NAMES
            for bonus_name in off_bonuses:
                self._send_message(self.BONUS_CHANGE_ROOM, 
                                   {'bonus_name': bonus_name,
                                    'enabled': 'false'})
        else:
            invalid_bonus_names = [bb for bb in on_bonuses 
                                   if bb not in BONUS_NAMES]
            assert len(invalid_bonus_names) == 0,\
                "{} are not in valid bonus names ({})".format(
                        invalid_bonus_names, BONUS_NAMES)
            off_bonuses = [bb for bb in BONUS_NAMES if bb not in on_bonuses]
            for bonus_name in off_bonuses:
                self._send_message(self.BONUS_CHANGE_ROOM, 
                                   {'bonus_name': bonus_name,
                                    'enabled': 'false'})
        # TODO: Much later, low priority, implement presets such as fatty?!
        
    def join_room(self, target_room, on_bonuses=None):
        """Doc string
        If the provided room exists, join it.
        Otherwise, create and configure the room,
        and then join it.
        :param target_room:
        :return:
        """

        for room in self.server.get('rooms', []):
            if room['name'] == target_room:
                break
        else:
            self.create_room(target_room)
        
        # join room
        self._send_message(self.JOIN_ROOM, {'room_name': target_room})
        self._wait_for_reply(self.message_id)
        assert (self.message_responses[self.message_id]['success'])
        self._send_message(self.ADD_PLAYER)
        self._wait_for_reply(self.message_id)
        assert (self.message_responses[self.message_id]['success'])
        self.set_bonuses(target_room=target_room, on_bonuses=on_bonuses)

    def send_action(self, action):
        self._send_message(self.PLAYER_MOVE, {'action': action})

    def send_ready(self):
        self._send_message(self.PLAYER_READY)
        self._wait_for_reply(self.message_id)
        assert (self.message_responses[self.message_id]['success'])

    def _process_recvd(self, recvd):
        messages = json.loads(recvd)
        for message in messages:
            self._parse_message(message)

    def _parse_message(self, message):
        if self.verbose:
            print("parsing message: ", message)

        if message[0] == 'position':
            pos = (message[1][1], message[1][2])
            if self.game['players'][message[1][0]]['printing']:
                if self.verbose:
                    print("____ADDING TRAIL")
                self.game['trails'][message[1][0]].append(pos)
            self.game['players'][message[1][0]]['position'] = pos

        elif message[0] == 'angle':
            self.game['players'][message[1][0]]['angle'] = message[1][1]

        elif message[0] == 'property':
            self.game['players'][message[1][0]][message[1][1]] = message[1][2]

        elif message[0] == 'die':
            if message[1][0] == self.player_id:
                self.player_alive = False

        elif message[0] == 'score:round':
            if message[1][0] == self.player_id:
                self.round_score = message[1][1]

        elif message[0] == "game:start":  # message received at start of subsequent rounds
            self.active_round = True

        elif message[0] == "room:game:start":  # message received at start of game
            self.active_game = True
            self._send_message(self.READY)

        elif message[0] == "game:stop":  # message received at end of round
            self.active_round = False

        elif message[0] == "round:new":  # message received at start of round
            pass  # might want to reset some parts of the state here?
            self.active_round = True
            self.round_score = 0
            self.game['trails'] = defaultdict(list)
            self.player_alive = True
            for k in self.game['players'].keys():
                self.game['players'][k]['printing'] = False

        elif message[0] == "end":  # message received at end of game
            self.active_game = False

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
        self._send_message(self.WHOAMI)
        response = self._recv_message()
        self.client_id = int(response[0][1])
        self._send_message(self.FETCH_ROOMS)

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

    def _send_message(self, message, message_args=None):
        """
        Send a message to the server, substituting values
        in message_args dict for placeholders.
        :param message:
        :param message_args:
        :return:
        """
        if message_args is None:
            message_args = {}
        self.message_id += 1
        self.ws.send(message.format(msg_id=self.message_id, client_id=self.client_id, player_id=self.player_id,
                                    player_name=self.name, player_color=self.color, **message_args))
