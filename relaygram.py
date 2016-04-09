import os.path
from argparse import ArgumentParser
from queue import Queue
from time import sleep

import twx.botapi
import yaml

from relaygram.irc import IRCHandler
from relaygram.telegram import TelegramHandler
from relaygram.channel_map import ChannelMap


class ConfigError(Exception):
    pass


class RelaygramBot:
    def __init__(self, verbosity, config_dir):
        self.verbosity = verbosity
        self.config_dir = config_dir
        self.config = yaml.load(open(os.path.join(config_dir, "relaygram.yaml"), "r"))
        try:
            self.channel_map = ChannelMap(os.path.join(config_dir, "channel_map.json"))
        except FileNotFoundError:
            self.channel_map = {}

        self.irc_queue = Queue()
        self.tg_queue = Queue()

        self.irc = IRCHandler(self.channel_map, self.verbosity, self.config, self.irc_queue, [self.tg_queue])
        self.telegram = TelegramHandler(self.channel_map, self.verbosity, self.config, self.tg_queue, [self.irc_queue])

        self.irc.run()
        self.telegram.run()

        while True:
            sleep(.1)

if __name__ == '__main__':
    parser = ArgumentParser(description="Relay chat between IRC and Telegram", epilog="https://github.com/Surye/relaygram")
    parser.add_argument("-c", dest="config_dir", default=os.path.expanduser("~/.relaygram"), help="Configuration Directory (default is ~/.relaygram)")
    parser.add_argument("-v", dest="verbosity", action='count', help="Verbosity Level (repeat for more verbose logging)")

    args = parser.parse_args()

    if not os.path.exists(args.config_dir):
        parser.error("Config directory {} does not exist".format(args.config_dir))

    bot = RelaygramBot(args.verbosity, args.config_dir)
