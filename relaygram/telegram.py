import twx.botapi
from threading import Thread


class ConfigError(Exception):
    pass


class IRCHandler:
    def __init__(self, verbosity, config, irc_queue, tg_queue):
        self.verbosity = verbosity
        self.config = config
        self.irc_queue = irc_queue
        self.tg_queue = tg_queue
        self.connect_request = {}

        # Setup Telegram bot
        try:
            self.twx = twx.botapi.TelegramBot(token=self.config['relaygram']['bot_token'])
            self.twx.update_bot_info().wait()  # Make sure we know who we are
        except KeyError:
            raise ConfigError("Error in configuration file, cannot find bot token.")

        self.thread = Thread(target=self.main_loop)

    def run(self):
        self.thread.start()
        return self

    def main_loop(self):
        last_update = 0
        while True:
            # Process Telegram Events
            updates = self.twx.get_updates(last_update).wait()
            for update in updates:
                last_update = update.update_id+1
                self.process_tg_msg(update)

    @staticmethod
    def chunker(seq, size):
        return (seq[pos:pos + size] for pos in range(0, len(seq), size))

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
                    for chans in self.chunker(channels, 3):
                        row = []
                        if len(chans) > 0: row.append(chans[0])
                        if len(chans) > 1: row.append(chans[1])
                        if len(chans) > 2: row.append(chans[2])
                        keyboard.append(row)
                    reply_markup = twx.botapi.ReplyKeyboardMarkup.create(keyboard, one_time_keyboard=True)
                    request = self.twx.send_message(update.message.chat.id, "IRC Channel not found, please connect", reply_markup=reply_markup).join()
                    self.connect_request[request.result.message_id] = update.message.chat.id