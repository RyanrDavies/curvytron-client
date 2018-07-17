from __future__ import absolute_import, division, print_function

import websocket
import json
import threading
from collections import defaultdict
import numpy as np

from skimage import draw

websocket.enableTrace(False)

__all__ = ['CurvytronClient']


def hex_to_rgb(hexstring):
    '''
    Assumes a color string of format #ffffff
    :param hexstring:
    :return:
    '''
    r = int(hexstring[1:3],16)
    g = int(hexstring[3:5], 16)
    b = int(hexstring[5:], 16)
    return (r,g,b)


class Game(object):

    def __init__(self):
        self.players = {}
        self.trails = defaultdict(list)


class Server(object):

    def __init__(self):
        self.address = ''
        self.rooms = []


class Player(object):

    def __init__(self, name, color, angle=None, printing=False, updated=False, position=None, draw_position=None):
        self.name = name
        self.color = color
        self.printing = printing
        self.updated = updated
        self.angle = angle
        self.position = position
        self.draw_position = draw_position
        self.alive=True

    def set_property(self, property, value):
        return setattr(self, property, value)


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
    BONUS_PRESETS = {'all': BONUS_NAMES,
                     'speed': ['BonusSelfFast', 'BonusEnemyFast'],
                     'supersize': ['BonusEnemyBig'],
                     'solo': ['BonusSelfSmall', 'BonusSelfSlow', 'BonusSelfFast', 'BonusSelfMaster',
                              'BonusGameBorderless', 'BonusGameClear'],
                     'none': None
                     }
    FETCH_ROOMS = '[["room:fetch"]]'
    WHOAMI = '[["whoami",null,{msg_id}]]'
    MAKE_ROOM = '[["room:create",{{"name":"{room_name}"}},{msg_id}]]'
    PLAYER_MOVE = '[["player:move",{{"avatar":{player_id},"move":{action}}}]]'
    JOIN_ROOM = '[["room:join",{{"name":"{room_name}","password":null}},{msg_id}]]'
    ADD_PLAYER = '[["player:add",{{"name":"{player_name}","color":"{player_color}"}},{msg_id}]]'
    READY = '[["ready"]]'
    PLAYER_READY = '[["room:ready", {{"player": {player_id}}}, {msg_id}]]'
    BONUS_CHANGE_ROOM = '[["room:config:bonus",{{"bonus":"{bonus_name}","enabled":{enabled}}}, {msg_id}]]'
    BOT_READY = '[["bot:ready"]]'
    MAX_SCORE = '[["room:config:max-score",{{"maxScore":{score}}},{msg_id}]]'

    def __init__(self, name='pythonClient', color="#ffffff", width=200, verbose=False, n_frames=3, stepped=False):
        super(CurvytronClient, self).__init__()

        self.message_id = -1

        self.ws = websocket.WebSocket()
        self.alive = threading.Event()
        self.alive.set()
        self.verbose = verbose
        self.connected = False

        self.name = name
        self.color = color
        self.game_state = None
        self.active_game = False
        self.active_round = False
        self.server = Server()
        self.game = Game()
        self.message_responses = {}
        self.player_alive = True
        self.round_score = 0
        self.bg_color = hex_to_rgb("#222222")

        self.stepped = stepped
        if not self.stepped:
            self.n_frames = 0
        else:
            self.n_frames = n_frames

        self.last_action = 0

        self.board_size = 0
        self.trails = None
        self.width = width
        self.scale = 1
        self.position = None
        self.angle = None

        self.client_id = None
        self.player_id = None

    def connect_to_server(self, server):
        """
        Connect to  the provided server and request client ID.
        :param server:
        :return:
        """
        self.ws.connect('ws://%s' % server)
        self.connected = True
        msg_id = self._send_message(self.WHOAMI)
        self._wait_for_reply(msg_id)
        self.client_id = self.message_responses[msg_id]
        self._send_message(self.FETCH_ROOMS)
        self.server.address = server

    def create_room(self, target_room=None):
        """Create room called target_room with bonuses listed in bonuses
        """
        for room in self.server.rooms:
            assert room['name'] != target_room, "Room already exists"
        self._send_message(self.MAKE_ROOM, {'room_name': target_room})
        self._wait_for_reply(self.message_id)
        assert (self.message_responses[self.message_id]['success'])

    def get_canvas(self):
        if self.stepped:
            frames = 0
            while frames < self.n_frames:
                while not all([self.game.players[player].updated for player in self.game.players.keys() if self.game.players[player].alive]):
                    continue
                for player in self.game.players.keys():
                    self.game.players[player].updated = False
                frames += 1
                self._send_message(self.BOT_READY)

        board = self.trails.copy()
        width = np.ceil(1.2 * self.scale)
        for player in self.game.players.keys():
            draw_x, draw_y = self.game.players[player].draw_position
            rr, cc = draw.circle(draw_y, draw_x, width / 2, shape=board.shape)
            color = hex_to_rgb(self.game.players[player].color)
            draw.set_color(board, (rr, cc), color)

        return board

    def join(self, timeout=None):
        self.alive.clear()
        self.ws.close()
        super(CurvytronClient, self).join(timeout)

    def join_room(self, target_room, on_bonuses=None, max_score=3):
        """Doc string
        If the provided room exists, join it.
        Otherwise, create and configure the room,
        and then join it.
        :param target_room:
        :param on_bonuses:
        :return:
        """
        for room in self.server.rooms:
            if room['name'] == target_room:
                joined_existing = True
                break
        else:
            joined_existing = False
            self.create_room(target_room)

        # join room
        msg_id = self._send_message(self.JOIN_ROOM, {'room_name': target_room})
        self._wait_for_reply(self.message_id)
        assert (self.message_responses[msg_id]['success'])
        self._add_players(self.message_responses[msg_id]['room']['players'])

        msg_id = self._send_message(self.ADD_PLAYER)
        self._wait_for_reply(msg_id)
        assert (self.message_responses[msg_id]['success']), self.message_responses[msg_id]
        if not joined_existing:
            self.set_bonuses(on_bonuses=on_bonuses)
            self.set_max_score(max_score=max_score)

    def run(self):
        self.ws.settimeout(0.05)
        while self.alive.isSet():
            if self.connected:
                try:
                    recvd = self.ws.recv()
                except websocket.WebSocketTimeoutException:
                    continue

                if recvd:
                    self._process_recvd(recvd)


    def send_action(self, action):
        if not self.last_action == action:
            self._send_message(self.PLAYER_MOVE, {'action': action})
            self.last_action = action
        if self.stepped:
            self._send_message(self.BOT_READY)

    def send_ready(self):
        assert (self.player_id is not None)
        msg_id = self._send_message(self.PLAYER_READY)
        self._wait_for_reply(msg_id)
        assert (self.message_responses[msg_id]['success'])

    def set_bonuses(self, on_bonuses=None):
        BONUS_NAMES = self.BONUS_NAMES

        if on_bonuses in self.BONUS_PRESETS:
            on_bonuses = self.BONUS_PRESETS[on_bonuses]

        if on_bonuses is None:
            off_bonuses = BONUS_NAMES
            for bonus_name in off_bonuses:
                self._send_message(self.BONUS_CHANGE_ROOM,
                                   {'bonus_name': bonus_name,
                                    'enabled': 'false'})
        else:
            invalid_bonus_names = [bb for bb in on_bonuses
                                   if bb not in BONUS_NAMES]
            assert len(invalid_bonus_names) == 0, "{} are not in valid bonus names ({})".format(invalid_bonus_names, BONUS_NAMES)
            off_bonuses = [bb for bb in BONUS_NAMES if bb not in on_bonuses]
            for bonus_name in off_bonuses:
                self._send_message(self.BONUS_CHANGE_ROOM,
                                   {'bonus_name': bonus_name,
                                    'enabled': 'false'})

    def set_max_score(self, max_score=3):
        self._send_message(self.MAX_SCORE,{'score':max_score})

    def _add_players(self, players):
        for player in players:
            self.game.players[player['id']] = Player(**{'name': player['name'],
                                                        'color': '#ffffff',
                                                        'printing': False})

    def _parse_message(self, message):
        if self.verbose:
            print("[{}] parsing message: {}".format(self.name, message))

        head = message[0]
        if len(message) > 1:
            body = message[1]

        if head == 'position':
            pid, x, y = body
            if self.stepped:
                self.game.players[pid].updated = True
            if self.game.players[pid].printing:
                self._update_trails(body)
            self._update_position(body)

        elif head == 'angle':
            pid, angle = body
            angle /= 100.0
            self.game.players[pid].angle = angle
            if pid == self.player_id:
                self.angle = angle

        elif head == 'property':
            self.game.players[body[0]].set_property(body[1], body[2])

        elif head == 'die':
            if body[0] == self.player_id:
                self.player_alive = False
            self.game.players[body[0]].alive = False

        elif head == 'score:round':
            if body[0] == self.player_id:
                self.round_score = body[1]

        elif head == "game:start":  # message received at start of subsequent rounds
            for player in self.game.players.keys():
                self.game.players[player].alive = True
            self.active_round = True

        elif head == "room:game:start":  # message received at start of game
            self.active_game = True
            self.board_size = int(np.sqrt((80 * 80) + ((len(self.game.players) - 1) * (80 * 80) / 5.0)))
            self.scale = float(self.width) / self.board_size
            self.trails = np.ones((self.width, self.width, 3), dtype=np.uint8) * 34  # set bg color
            self._send_message(self.READY)

        elif head == "game:stop":  # message received at end of round
            self.active_round = False

        elif head == "round:new":  # message received at start of round
            self.last_action = 0
            self.active_round = True
            self.round_score = 0
            self.game.trails = defaultdict(list)
            self.player_alive = True
            for k in self.game.players.keys():
                self.game.players[k].printing = False
            self.trails = np.ones((self.width, self.width, 3), dtype=np.uint8) * 34  # set bg color

        elif head == "end":  # message received at end of game
            self.active_game = False

        elif head == 'room:join':
            player_details = body['player']
            self.game.players[player_details['id']] = Player(**{'name': player_details['name'],
                                                                'color': player_details['color'],
                                                                'printing': False})
            if player_details['name'] == self.name and player_details['client'] == self.client_id:
                self.player_id = player_details['id']

        elif head == 'room:open':
            self.server.rooms.append(body)

        elif head == 'room:leave':
            _ = self.game.players.pop(body['player'])

        elif isinstance(head, int):
            self.message_responses[head] = body

        else:
            pass

    def _process_recvd(self, recvd):
        messages = json.loads(recvd)
        for message in messages:
            self._parse_message(message)

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
        if '{msg_id}' in message:
            self.message_id += 1
        self.ws.send(message.format(msg_id=self.message_id, client_id=self.client_id, player_id=self.player_id,
                                    player_name=self.name, player_color=self.color, **message_args))
        if '{msg_id}' in message:
            return self.message_id

    def _update_position(self, message):
        pid, x, y = message
        draw_x = (x / 100.0) * self.scale
        draw_y = (y / 100.0) * self.scale

        if pid == self.player_id:
            self.position = (draw_y, draw_x)
        self.game.players[pid].position=(x,y)
        self.game.players[pid].draw_position = (draw_x,draw_y)

    def _update_trails(self, message):
        pid, x, y = message
        width = 1.2 * self.scale
        draw_x = (x / 100.0) * self.scale
        draw_y = (y / 100.0) * self.scale
        rr, cc = draw.circle(draw_y, draw_x, width / 2, shape=self.trails.shape)
        color = hex_to_rgb(self.game.players[pid].color)
        draw.set_color(self.trails, (rr,cc), color)

    def _wait_for_reply(self, message_id):
        while message_id not in self.message_responses:
            continue
