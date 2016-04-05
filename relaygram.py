import irc.client as irc
import twx.botapi

import yaml

from argparse import ArgumentParser
import os.path

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

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

        # Setup Telegram bot
        try:
            self.twx = twx.botapi.TelegramBot(token=self.config['relaygram']['bot_token'])
            self.twx.update_bot_info().wait()  # Make sure we know who we are
        except KeyError:
            raise ConfigError("Error in configuration file, cannot find bot token.")
        self.connect_request = {}

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

        # Run main processing loop
        # TODO: asyncio?
        self.main_loop()

    def main_loop(self):
        last_update = 0
        while True:
            # Process Telegram Events
            updates = self.twx.get_updates(last_update).wait()
            for update in updates:
                last_update = update.update_id+1
                self.process_tg_msg(update)

            self.irc.process_once()

    def irc_pubmsg(self, connection, event):
        self.process_irc_msg(connection, event)

    def process_irc_msg(self, connection, event):
        pass

    def process_tg_msg(self, update):
        if update.message:
            if update.message.chat.id not in self.channel_map:
                if update.message.reply_to_message and update.message.reply_to_message.message_id in self.connect_request:
                    print("Connect to {}".format(update.message.text))
                else:
                    keyboard = []
                    channels = []
                    for server_name, server_params in self.config['irc']['servers'].items():
                        for channel in server_params['channels']:
                            channels.append('{} - {}'.format(server_name, channel))
                    for chans in chunker(channels, 3):
                        row = []
                        if len(chans) > 0: row.append(chans[0])
                        if len(chans) > 1: row.append(chans[1])
                        if len(chans) > 2: row.append(chans[2])
                        keyboard.append(row)
                    reply_markup = twx.botapi.ReplyKeyboardMarkup.create(keyboard, one_time_keyboard=True)
                    request = self.twx.send_message(update.message.chat.id, "IRC Channel not found, please connect", reply_markup=reply_markup).join()
                    self.connect_request[request.result.message_id] = update.message.chat.id

if __name__ == '__main__':
    parser = ArgumentParser(description="Relay chat between IRC and Telegram", epilog="https://github.com/Surye/relaygram")
    parser.add_argument("-c", dest="config_dir", default=os.path.expanduser("~/.relaygram"), help="Configuration Directory (default is ~/.relaygram)")
    parser.add_argument("-v", dest="verbosity", action='count', help="Verbosity Level (repeat for more verbose logging)")

    args = parser.parse_args()

    if not os.path.exists(args.config_dir):
        parser.error("Config directory {} does not exist".format(args.config_dir))

    bot = RelaygramBot(args.verbosity, args.config_dir)
