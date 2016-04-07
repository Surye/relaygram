from threading import Thread
from irc import client as irc


class IRCHandler:
    def __init__(self, verbosity, config, irc_queue, tg_queue):
        self.verbosity = verbosity
        self.config = config
        self.irc_queue = irc_queue
        self.tg_queue = tg_queue

        # Build up IRC connections
        self.irc = irc.Reactor()
        self.irc.add_global_handler("pubmsg", handler=self.irc_pubmsg)
        self.irc_servers = {}
        for server_name, server_params in self.config['irc']['servers'].items():
            irc_server = self.irc.server()
            irc_server.connect(server_params['hostname'], server_params['port'], server_params['nickname'])
            for channel in server_params['channels']:
                irc_server.join(channel)
            self.irc_servers[server_name] = irc_server

        self.thread = Thread(target=self.main_loop)

    def run(self):
        self.thread.start()
        return self

    def main_loop(self):
        self.irc.process_forever()

    def irc_pubmsg(self, connection, event):
        self.process_irc_msg(connection, event)

    def process_irc_msg(self, connection, event):
        pass
