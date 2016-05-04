from threading import Thread
from irc import client as irc
from queue import Empty
from time import sleep
import logging
from relaygram import events


class IRCHandler:
    def __init__(self, channel_map, config, my_queue, out_queues):
        self.log = logging.getLogger("relaygram.irc")
        self.channel_map = channel_map
        self.config = config
        self.my_queue = my_queue
        self.out_queues = out_queues

        self.initalized_servers = []

        # Build up IRC connections
        self.irc = irc.Reactor()

        # Message Events
        self.irc.add_global_handler("pubmsg", handler=self.irc_pubmsg)
        self.irc.add_global_handler("topic", handler=self.irc_topic)
        self.irc.add_global_handler("action", handler=self.irc_action)
        self.irc.add_global_handler("join", handler=self.irc_join)
        self.irc.add_global_handler("part", handler=self.irc_part)
        self.irc.add_global_handler("quit", handler=self.irc_quit)
        self.irc.add_global_handler("kick", handler=self.irc_kick)

        # System Events
        self.irc.add_global_handler("namreply", handler=self.irc_namreply)
        self.irc.add_global_handler("disconnect", handler=self.irc_disconnect)
        self.irc.add_global_handler("nicknameinuse", handler=self.irc_nicknameinuse)
        self.irc.add_global_handler("umode", handler=self.irc_umode)

        self.irc_servers = {}
        self.irc_channels = {}
        for server_name, server_params in self.config['irc']['servers'].items():
            self.initialize_server(server_params)

        self.thread = Thread(target=self.main_loop)

    def initialize_server(self, server_params):
        irc_server = self.irc.server()
        irc_server.connect(server_params['hostname'], server_params['port'], server_params['nickname'])
        self.irc_channels[irc_server.server] = {}
        for channel in server_params['channels']:
            self.irc_channels[irc_server.server][channel] = set()

        self.irc_servers[server_params['hostname']] = irc_server

    def irc_umode(self, connection, event):
        #  Set when server connection is finished, some servers don't like early join messages.
        if connection not in self.initalized_servers:
            for channel in self.irc_channels[connection.server].keys():
                connection.join(channel)
        self.initalized_servers.append(connection)

    def run(self):
        self.thread.start()
        return self

    def main_loop(self):
        while True:
            self.irc.process_once()
            self.process_queue_once()
            sleep(.1)

    def process_queue_once(self):
        try:
            self.process_event(self.my_queue.get_nowait())
        except Empty:
            pass

    def process_event(self, event):
        src_id = event.src[1]
        [server, channel] = self.channel_map.get_dest("tg", src_id).split(":")
        irc_config = self.config['irc']

        if event.type is events.Message:
            msg = irc_config['message_pattern'].format(nick=event.user, msg=event.msg)
        elif event.type is events.Join:
            msg = irc_config['join_pattern'].format(nick=event.user, msg=event.msg)
        elif event.type is events.Part:
            msg = irc_config['part_pattern'].format(nick=event.user, msg=event.msg)
        elif event.type is events.Kick:
            msg = irc_config['kick_pattern'].format(nick=event.user, msg=event.msg)
        elif event.type is events.Topic:
            msg = irc_config['topic_pattern'].format(nick=event.user, msg=event.msg)
        elif event.type is events.Action:
            msg = irc_config['topic_pattern'].format(nick=event.user, msg=event.msg)
        else:
            msg = None

        if msg:
            self.log.info("Sending to irc: {msg}".format(msg=msg))
            for line in msg.splitlines():
                for msg in [line[i:i+400] for i in range(0, len(line), 400)]:
                    self.irc_servers[server].privmsg(channel, msg)
                    sleep(0.75)

    def irc_pubmsg(self, connection, event):
        item = events.Message(src=(connection.server, event.target), user=event.source.nick, msg=event.arguments[0])
        [queue.put_nowait(item) for queue in self.out_queues]

    def irc_topic(self, connection, event):
        item = events.Topic(src=(connection.server, event.target), user=event.source.nick, msg=event.arguments[0])
        [queue.put_nowait(item) for queue in self.out_queues]

    def irc_action(self, connection, event):
        item = events.Action(src=(connection.server, event.target), user=event.source.nick, msg=event.arguments[0])
        [queue.put_nowait(item) for queue in self.out_queues]

    def irc_join(self, connection, event):
        self.irc_channels[connection.server][event.target].add(event.source.nick)

        item = events.Join(src=(connection.server, event.target), user=event.source.nick)
        [queue.put_nowait(item) for queue in self.out_queues]

    def irc_part(self, connection, event):
        item = events.Part(src=(connection.server, event.target), user=event.source.nick)
        [queue.put_nowait(item) for queue in self.out_queues]

    def irc_quit(self, connection, event):
        for channel, nick_list in self.irc_channels[connection.server].items():
            if event.source.nick in nick_list:
                nick_list.discard(event.source.nick)
                item = events.Part(src=(connection.server, channel), user=event.source.nick)
                [queue.put_nowait(item) for queue in self.out_queues]

    def irc_kick(self, connection, event):
        item = events.Kick(src=(connection.server, event.target), user=event.source.nick, msg=event.arguments)
        [queue.put_nowait(item) for queue in self.out_queues]

    def irc_nicknameinuse(self, connection, event):
        self.log.warning("Nickname in use, using {}".format(connection.get_nickname() + "_"))
        connection.nick(connection.get_nickname() + "_")

        for channel in self.irc_channels[connection.server].keys():
            connection.join(channel)

    def irc_namreply(self, connection, event):
        ch_type, channel, nick_list = event.arguments

        for nick in nick_list.split():
            nick_modes = []

            if nick[0] in connection.features.prefix:
                nick_modes.append(connection.features.prefix[nick[0]])
                nick = nick[1:]

            self.irc_channels[connection.server][channel].add(nick)

    def irc_disconnect(self, connection, event):
        # TODO Reconnect
        self.log.error("Disconnected from {}".format(connection.server))
