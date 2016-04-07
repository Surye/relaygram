import os.path
from argparse import ArgumentParser
from queue import Queue

import twx.botapi
import yaml

from relaygram.irc import IRCHandler

class ConfigError(Exception):
    pass


class RelaygramBot(object):
    def __init__(self, verbosity, config_dir):
        self.verbosity = verbosity
        self.config_dir = config_dir
        self.config = yaml.load(open(os.path.join(config_dir, "relaygram.yaml"), "r"))
        try:
            self.channel_map = yaml.load(open(os.path.join(config_dir, "channel_map.yaml"), "r"))
        except FileNotFoundError:
            self.channel_map = {}

        self.irc_queue = Queue()
        self.tg_queue = Queue()

        self.irc = IRCHandler(self.verbosity, self.config, self.irc_queue, self.tg_queue)
        self.telegram = IRCHandler(self.verbosity, self.config, self.irc_queue, self.tg_queue)

        self.irc.run()
        self.telegram.run()

if __name__ == '__main__':
    parser = ArgumentParser(description="Relay chat between IRC and Telegram", epilog="https://github.com/Surye/relaygram")
    parser.add_argument("-c", dest="config_dir", default=os.path.expanduser("~/.relaygram"), help="Configuration Directory (default is ~/.relaygram)")
    parser.add_argument("-v", dest="verbosity", action='count', help="Verbosity Level (repeat for more verbose logging)")

    args = parser.parse_args()

    if not os.path.exists(args.config_dir):
        parser.error("Config directory {} does not exist".format(args.config_dir))

    bot = RelaygramBot(args.verbosity, args.config_dir)
