from queue import Empty
from . import events
from time import sleep
import twx.botapi
from threading import Thread


class ConfigError(Exception):
    pass


class TelegramHandler:
    def __init__(self, channel_map, verbosity, config, my_queue, out_queues):
        self.channel_map = channel_map
        self.verbosity = verbosity
        self.config = config
        self.my_queue = my_queue
        self.out_queues = out_queues
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
            self.process_queue_once()
            sleep(.1)

    def process_queue_once(self):
        try:
            self.process_event(self.my_queue.get_nowait())

        except Empty:
            pass  # Don't Care

    def process_event(self, event):
        dest = self.channel_map.get_dest("irc", "{}:{}".format(event.src[0], event.src[1]))
        if event.type is events.Message:
            self.twx.send_message(dest, "<{}> {}".format(event.user, event.msg))
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


    @staticmethod
    def build_keyboard(buttons):
        # TODO: Implement in twx.botapi
        def chunker(seq):
            return (seq[pos:pos + 3] for pos in range(0, len(seq), 3))

        keyboard = []
        for button in chunker(buttons):
            row = []
            if len(button) > 0:
                row.append(button[0])
            if len(button) > 1:
                row.append(button[1])
            if len(button) > 2:
                row.append(button[2])
            keyboard.append(row)
        return keyboard

    def process_tg_msg(self, update):
        if update.message:
            if self.channel_map.get_dest("tg", update.message.chat.id) is None:
                self.process_mapping(update)
            else:
                item = events.Message(src=("tg", update.message.chat.id), user=update.message.sender.username, msg=update.message.text)
                [queue.put_nowait(item) for queue in self.out_queues]

    def process_mapping(self, update):
        if update.message.reply_to_message and update.message.reply_to_message.message_id in self.connect_request:
            try:
                [server_name, channel_name] = update.message.text.rsplit(": ", 1)
            except ValueError:
                print("Bad choice, could not connect channels")
            server_host = self.config["irc"]["servers"][server_name]["hostname"]
            self.channel_map.set_mapping(update.message.chat.id, "{}:{}".format(server_host, channel_name))
            print("Connect to {}:{}".format(server_name, channel_name))
        else:
            channels = []
            for server_name, server_params in self.config['irc']['servers'].items():
                for channel in server_params['channels']:
                    channels.append('{}: {}'.format(server_name, channel))

            reply_markup = twx.botapi.ReplyKeyboardMarkup.create(self.build_keyboard(channels), one_time_keyboard=True)
            request = self.twx.send_message(update.message.chat.id, "IRC Channel not found, please connect", reply_markup=reply_markup).join()
            self.connect_request[request.result.message_id] = update.message.chat.id

