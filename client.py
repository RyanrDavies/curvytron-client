import websocket
import json
import threading
from collections import defaultdict
import numpy as np

from skimage import draw

websocket.enableTrace(False)

__all__ = ['CurvytronClient', 'CurvytronClientBase']

class CurvytronClientBase(threading.Thread):
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
    BOT_READY = '[["BOT:READY"]]'
    
    def __init__(self, name='pythonClient', color="#ffffff",width=200, verbose=False,n_frames=3,stepped=False):
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
        self.server = {'address': '', 'rooms': []}
        self.game = {'players': {}, 'trails': defaultdict(list)}
        self.message_responses = {}
        self.player_alive = True
        self.round_score = 0

        self.stepped = stepped
        if not self.stepped:
            self.n_frames = 0
        else:
            self.n_frames = n_frames

        self.last_action = 0

        self.board_size = 0
        self.trails = None
        self.heads = None
        self.width = width
        self.scale = 1
        self.position = None
        self.angle = None

        self.client_id = None
        self.player_id = None

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
            assert len(invalid_bonus_names) == 0,\
                "{} are not in valid bonus names ({})".format(
                        invalid_bonus_names, BONUS_NAMES)
            off_bonuses = [bb for bb in BONUS_NAMES if bb not in on_bonuses]
            for bonus_name in off_bonuses:
                self._send_message(self.BONUS_CHANGE_ROOM, 
                                   {'bonus_name': bonus_name,
                                    'enabled': 'false'})
        
    def join_room(self, target_room, on_bonuses=None):
        """Doc string
        If the provided room exists, join it.
        Otherwise, create and configure the room,
        and then join it.
        :param target_room:
        :return:
        """

        # FIXME: this check doesn't work if room is created before the client connects
        # This happens when we miss the reply to the fetch messages because this it happens too soon after starting.
        # Think it's fixed, but leaving this until we're sure.
        for room in self.server.get('rooms', []):
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
        assert (self.message_responses[msg_id]['success'])
        if not joined_existing:
            self.set_bonuses(on_bonuses=on_bonuses)

    def send_action(self, action):
        # Only send action if it's different from the last one to reduce
        # number of messges being sent.
        if not(self.last_action) == action:
            self._send_message(self.PLAYER_MOVE, {'action': action})
            self.last_action = action
        if self.stepped:
            self._send_message(self.BOT_READY)

    def send_ready(self):
        msg_id = self._send_message(self.PLAYER_READY)
        self._wait_for_reply(msg_id)
        assert (self.message_responses[msg_id]['success'])

    def _process_recvd(self, recvd):
        messages = json.loads(recvd)
        for message in messages:
            self._parse_message(message)

    def _parse_message(self, message):
        if self.verbose:
            print("[{}] parsing message: {}".format(self.name, message))

        if message[0] == 'position':
            pid,x,y = message[1]
            if self.stepped:
                self.game['players'][pid]['updated'] = True
            if self.game['players'][pid]['printing']:
                #self.game['trails'][pid].append((x,y))
                self._update_trails(message[1])
            #self.game['players'][pid]['position'] = (x,y)
            self._update_position(message[1])

        elif message[0] == 'angle':
            pid,angle = message[1]
            angle /= 100.0
            self.game['players'][pid]['angle'] = angle
            if pid == self.player_id:
                self.angle = angle

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
            self.board_size = int(np.sqrt((80*80) + ((len(self.game['players']) -1) * (80*80)/ 5.0)))
            self.scale = float(self.width) / self.board_size
            self.trails = np.zeros((self.width,self.width),dtype=np.uint8)
            self.heads = np.zeros((self.width, self.width), dtype=np.uint8)
            self._send_message(self.READY)

        elif message[0] == "game:stop":  # message received at end of round
            self.active_round = False

        elif message[0] == "round:new":  # message received at start of round
            #pass  # might want to reset some parts of the state here?
            self.last_action = 0
            self.active_round = True
            self.round_score = 0
            self.game['trails'] = defaultdict(list)
            self.player_alive = True
            for k in self.game['players'].keys():
                self.game['players'][k]['printing'] = False
            self.heads = np.zeros((self.width, self.width), dtype=np.uint8)
            self.trails = np.zeros((self.width, self.width), dtype=np.uint8)

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
        self.server['address'] = server



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
        if '{msg_id}' in message:
            self.message_id += 1
        self.ws.send(message.format(msg_id=self.message_id, client_id=self.client_id, player_id=self.player_id,
                                    player_name=self.name, player_color=self.color, **message_args))
        if '{msg_id}' in message:
            return self.message_id

    def _add_players(self, players):
        for player in players:
            self.game['players'][player['id']] = {'name': player['name'],
                                                  'color': '#ffffff',
                                                  'printing': False}

    def _update_position(self,message):
        raise NotImplementedError


    def _update_trails(self,message):
        raise NotImplementedError
        

    def get_canvas(self):
        frames = 0
        while frames < self.n_frames:
            while not all([self.game['players'][player].get('updated',False) for player in self.game['players'].keys()]):
                continue
            for player in self.game['players'].keys():
                self.game['players'][player]['updated'] = False
            frames += 1
            self._send_message(self.BOT_READY)
        return np.clip(self.trails + self.heads,0,1)


class CurvytronClient(CurvytronClientBase):

    def __init__(self,*args,**kwargs):
        super(CurvytronClient, self).__init__(*args,**kwargs)

    def _update_position(self,message):
        width = np.ceil(1.2*self.scale)
        draw_x = (x/100.0) * self.scale
        draw_y = (y/100.0) * self.scale

        if pid == self.player_id:
            self.position = (draw_y, draw_x)

        rr,cc = draw.circle(draw_y,draw_x,width/2,shape=self.heads.shape)
        self.heads = np.zeros((self.width, self.width), dtype=np.uint8)
        self.heads[rr,cc] = 1

    def _update_trails(self,message):
        pid,x,y = message
        width = 1.2*self.scale
        draw_x = (x/100.0) * self.scale
        draw_y = (y/100.0) * self.scale
        rr,cc = draw.circle(draw_y,draw_x,width/2,shape=self.trails.shape)
        self.trails[rr,cc] = 1

    def get_canvas(self):
        frames = 0
        while frames < self.n_frames:
            while not all([self.game['players'][player].get('updated',False) for player in self.game['players'].keys()]):
                continue
            for player in self.game['players'].keys():
                self.game['players'][player]['updated'] = False
            frames += 1
            self._send_message(self.BOT_READY)
        return np.clip(self.trails,0,1)
