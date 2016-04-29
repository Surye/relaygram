#!/usr/bin/env python3

import os.path
from argparse import ArgumentParser
from queue import Queue
from time import sleep
import yaml
import logging

from relaygram.irc import IRCHandler
from relaygram.telegram import TelegramHandler
from relaygram.http_server import HTTPHandler
from relaygram.channel_map import ChannelMap


class ConfigError(Exception):
    pass


class RelaygramBot:
    def __init__(self, verbosity, config_dir):
        self.log = logging.getLogger("relaygram")
        self.verbosity = verbosity
        self.config_dir = config_dir
        self.config = yaml.load(open(os.path.join(config_dir, "relaygram.yaml"), "r"))
        self.config['config_dir'] = config_dir
        self.config['media_dir'] = os.path.join(config_dir, "media")
        if not os.path.exists(self.config['media_dir']):
            os.mkdir(self.config['media_dir'])

        # Setup Logging
        if verbosity:
            if verbosity == 1:
                logging.basicConfig(level=logging.INFO)
            elif verbosity >= 2:
                logging.basicConfig(level=logging.DEBUG)

        logging.getLogger("requests").setLevel(logging.WARNING)  # Quiet requests, too verbose at INFO

        try:
            self.channel_map = ChannelMap(os.path.join(config_dir, "channel_map.json"))
        except FileNotFoundError:
            self.channel_map = {}

        self.irc_queue = Queue()
        self.tg_queue = Queue()

        self.irc = IRCHandler(self.channel_map, self.config, self.irc_queue, [self.tg_queue])
        self.telegram = TelegramHandler(self.channel_map, self.config, self.tg_queue, [self.irc_queue])

        self.irc.run()
        self.telegram.run()

        # Media Hoster
        if self.config['media']['port'] and self.config['media']['port'] is not 0:
            self.httpd = HTTPHandler(self.config)
            self.httpd.run()

        while True:
            sleep(.1)

if __name__ == '__main__':
    parser = ArgumentParser(description="Relay chat between IRC and Telegram", epilog="https://github.com/Surye/relaygram")
    parser.add_argument("-c", dest="config_dir", default=os.path.expanduser("~/.relaygram"), help="Configuration Directory (default is ~/.relaygram)")
    parser.add_argument("-v", dest="verbosity", action='count', help="Verbosity Level (repeat for more verbose logging)")

    args = parser.parse_args()

    if not os.path.exists(args.config_dir):
        parser.error("Config directory {} does not exist. Please create it and copy relaygram.example.yaml to it as relaygram.yaml.".format(args.config_dir))

    bot = RelaygramBot(args.verbosity, args.config_dir)
