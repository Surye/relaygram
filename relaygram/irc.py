from threading import Thread
from irc import client as irc
from queue import Empty
from time import sleep
from . import events

class IRCHandler:
    def __init__(self, channel_map, verbosity, config, my_queue, out_queues):
        self.channel_map = channel_map
        self.verbosity = verbosity
        self.config = config
        self.my_queue = my_queue
        self.out_queues = out_queues

        # Build up IRC connections
        self.irc = irc.Reactor()
        self.irc.add_global_handler("pubmsg", handler=self.irc_pubmsg)
        self.irc.add_global_handler("topic", handler=self.irc_topic)
        self.irc.add_global_handler("action", handler=self.irc_action)
        self.irc.add_global_handler("join", handler=self.irc_join)
        self.irc.add_global_handler("part", handler=self.irc_part)
        self.irc.add_global_handler("kick", handler=self.irc_kick)

        self.irc_servers = {}
        for server_name, server_params in self.config['irc']['servers'].items():
            irc_server = self.irc.server()
            irc_server.connect(server_params['hostname'], server_params['port'], server_params['nickname'])
            for channel in server_params['channels']:
                irc_server.join(channel)
            self.irc_servers[server_params['hostname']] = irc_server

        self.thread = Thread(target=self.main_loop)

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

        if event.type is events.Message:
            self.irc_servers[server].privmsg(channel, "<{}> {}".format(event.user, event.msg))
        elif event.type is events.Join:
            pass
        elif event.type is events.Part:
            pass
        elif event.type is events.Kick:
            pass
        elif event.type is events.Topic:
            pass
        elif event.type is events.Action:
            pass

    def irc_pubmsg(self, connection, event):
        item = events.Message(src=(connection.server, event.target), user=event.source, msg=event.arguments[0])
        [queue.put_nowait(item) for queue in self.out_queues]

    def irc_topic(self, connection, event):
        item = events.Topic(src=(connection.server, event.target), user=event.source, msg=event.arguments[0])
        [queue.put_nowait(item) for queue in self.out_queues]

    def irc_action(self, connection, event):
        item = events.Action(src=(connection.server, event.target), user=event.source, msg=event.arguments[0])
        [queue.put_nowait(item) for queue in self.out_queues]

    def irc_join(self, connection, event):
        item = events.Join(src=(connection.server, event.target), user=event.source)
        [queue.put_nowait(item) for queue in self.out_queues]

    def irc_part(self, connection, event):
        item = events.Part(src=(connection.server, event.target), user=event.source)
        [queue.put_nowait(item) for queue in self.out_queues]

    def irc_kick(self, connection, event):
        item = events.Kick(src=(connection.server, event.target), user=event.source, msg=event.arguments)
        [queue.put_nowait(item) for queue in self.out_queues]

