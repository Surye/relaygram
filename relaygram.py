import irc
import twx.botapi

from configobj import ConfigObj

import argparse


class RelaygramBot(object):
    pass

if __name__ == '__main__':
    args = argparse.ArgumentParser(description="Relay chat between IRC and Telegram", epilog="https://github.com/Surye/relaygram")
    args.add_argument("-c", dest="config_dir", default="~/.relaygram", help="Configuration Directory (default is ~/.relaygram)")
    args.add_argument("-v", dest="verbosity", action='count', help="Verbosity Level (repeat for more verbose logging)")
    args.print_help()

