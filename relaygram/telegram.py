import os
from queue import Empty
from . import events
from time import sleep
import twx.botapi
from threading import Thread
import random
import string
import logging
import mimetypes
import re


class ConfigError(Exception):
    pass


class TelegramHandler:
    def __init__(self, channel_map, config, my_queue, out_queues):
        self.log = logging.getLogger("relaygram.telegram")
        self.channel_map = channel_map
        self.config = config
        self.my_queue = my_queue
        self.out_queues = out_queues
        self.connect_request = {}
        self.seen_usernames = set()

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
            if updates:
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

    def add_mentions(self, msg):
        if self.config['telegram']['convert_mentions']:
            for username in self.seen_usernames:
                msg = re.sub(r'\b' + re.escape(username) + r'\b', "@{}".format(username), msg, flags=re.I)
        return msg

    def process_event(self, event):
        dest = self.channel_map.get_dest("irc", "{}:{}".format(event.src[0], event.src[1]))
        tgconfig = self.config['telegram']

        if event.type is events.Message:
            msg = tgconfig['message_pattern'].format(nick=event.user, msg=self.add_mentions(event.msg))
        elif event.type is events.Join:
            msg = tgconfig['join_pattern'].format(nick=event.user, msg=event.msg)
        elif event.type is events.Part:
            msg = tgconfig['part_pattern'].format(nick=event.user, msg=event.msg)
        elif event.type is events.Kick:
            msg = tgconfig['kick_pattern'].format(kicker=event.user, nick=event.msg[0], msg=event.msg[1])
        elif event.type is events.Topic:
            msg = tgconfig['topic_pattern'].format(nick=event.user, msg=event.msg)
        elif event.type is events.Action:
            msg = tgconfig['action_pattern'].format(nick=event.user, msg=self.add_mentions(event.msg))
        else:
            msg = None

        if msg:
            self.log.info("Sending to telegram: {msg}".format(msg=msg))
            self.twx.send_message(dest, msg)

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
                message = update.message
                user = update.message.sender.username
                self.seen_usernames.add(user)

                src = ("tg", message.chat.id)

                if message.photo:
                    file = self.twx.get_file(message.photo[-1].file_id).join().result
                    filename = self.store_telegram_media(file)
                    mimetype = mimetypes.guess_type(filename)[0]
                    file_size = self.sizeof_fmt(message.photo[-1].file_size)

                    msg = "[{mime}] {url} [{width}x{height}] [{file_size}]".format(mime=mimetype, url=self.config['media']['base_url'] + filename,
                                                                                   width=message.photo[-1].width, height=message.photo[-1].height, file_size=file_size)
                    if message.caption:
                        msg = "{msg} {caption}".format(msg=msg, caption=message.caption)
                    item = events.Message(src=src, user=user, msg=msg)

                elif message.audio:
                    file = self.twx.get_file(message.audio.file_id).join().result
                    filename = self.store_telegram_media(file)
                    mimetype = mimetypes.guess_type(filename)[0]
                    file_size = self.sizeof_fmt(message.audio.file_size)

                    duration = self.time_fmt(message.audio.duration)

                    msg = "[{mime}] {url} [{duration}] [{file_size}]".format(mime=mimetype, url=self.config['media']['base_url'] + filename,
                                                                            duration=duration, file_size=file_size)
                    item = events.Message(src=src, user=user, msg=msg)

                elif message.sticker:
                    file = self.twx.get_file(message.sticker.file_id).join().result
                    filename = self.store_telegram_media(file)
                    mimetype = mimetypes.guess_type(filename)[0]
                    file_size = self.sizeof_fmt(message.sticker.file_size)

                    msg = "[sticker] {url} [{width}x{height}] [{file_size}]".format(mime=mimetype, url=self.config['media']['base_url'] + filename,
                                                                                   width=message.sticker.width, height=message.sticker.height, file_size=file_size)
                    item = events.Message(src=src, user=user, msg=msg)

                elif message.video:
                    file = self.twx.get_file(message.video.file_id).join().result
                    filename = self.store_telegram_media(file)
                    mimetype = mimetypes.guess_type(filename)[0]
                    file_size = self.sizeof_fmt(message.video.file_size)

                    duration = self.time_fmt(message.video.duration)

                    msg = "[{mime}] {url} [{width}x{height}] [{duration}] [{file_size}]".format(mime=mimetype, url=self.config['media']['base_url'] + filename,
                                                                                               duration=duration, width=message.video.width, height=message.video.height,
                                                                                               file_size=file_size)
                    if message.caption:
                        msg = "{msg} {caption}".format(msg=msg, caption=message.caption)

                    item = events.Message(src=src, user=user, msg=msg)

                elif message.voice:
                    file = self.twx.get_file(message.voice.file_id).join().result
                    filename = self.store_telegram_media(file)
                    mimetype = mimetypes.guess_type(filename)[0]
                    file_size = self.sizeof_fmt(message.voice.file_size)

                    duration = self.time_fmt(message.voice.duration)

                    msg = "[voice msg] {url} [{duration}] [{file_size}]".format(mime=mimetype, url=self.config['media']['base_url'] + filename,
                                                                                duration=duration, file_size=file_size)
                    item = events.Message(src=src, user=user, msg=msg)

                elif message.document:
                    file = self.twx.get_file(message.document.file_id).join().result
                    filename = self.store_telegram_media(file)
                    mimetype = mimetypes.guess_type(filename)[0]
                    file_size = self.sizeof_fmt(message.document.file_size)

                    size = message.document.file_size

                    msg = "[{mime}] {url} [{file_size}]".format(mime=mimetype, url=self.config['media']['base_url'] + filename,
                                                               file_size=file_size)

                    item = events.Message(src=src, user=user, msg=msg)

                elif message.contact:
                    if message.contact.last_name:
                        msg = "[contact] {contact.first_name} {contact.last_name} - {contact.phone_number}".format(contact=message.contact)
                    else:
                        msg = "[contact] {contact.first_name} {contact.last_name} - {contact.phone_number}".format(contact=message.contact)
                    item = events.Message(src=src, user=user, msg=msg)

                elif message.venue:
                    msg = "[venue] {venue.title} {venue.address} [https://www.google.com/maps/?q={location.latitude},{location.longitude}]".format(location=message.location,
                                                                                                                                                   venue=message.venue)
                    item = events.Message(src=src, user=user, msg=msg)

                elif message.location:
                    msg = "[location] https://www.google.com/maps/?q={location.latitude},{location.longitude}".format(location=message.location)
                    item = events.Message(src=src, user=user, msg=msg)

                elif message.left_chat_member:
                    item = events.Part(src=src, user=(message.left_chat_member.username or
                                                      "{} {}".format(message.left_chat_member.first_name, message.left_chat_member.last_name)))
                elif message.new_chat_member:
                    item = events.Join(src=src, user=(message.new_chat_member.username or
                                                      "{} {}".format(message.new_chat_member.first_name, message.new_chat_member.last_name)))
                else:
                    # Plain message
                    item = events.Message(src=src, user=user, msg=message.text)

                [queue.put_nowait(item) for queue in self.out_queues]

    @staticmethod
    def time_fmt(runtime):
        m, s = divmod(runtime, 60)
        h, m = divmod(m, 60)
        duration = "{}:{:02}:{:02}".format(h, m, s)
        return duration

    @staticmethod
    def sizeof_fmt(num, suffix='B'):
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Yi', suffix)

    def store_telegram_media(self, file):
        if 'randomize_name_length' in self.config['media'] and self.config['media']['randomize_name_length'] > 0:
            file_basename = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(self.config['media']['randomize_name_length']))
        else:
            file_basename = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(8))

        ext = os.path.splitext(file.file_path)[1]
        filename = file_basename + ext
        out_file = os.path.join(self.config['media_dir'], filename)
        self.twx.download_file(file_path=file.file_path, out_file=open(out_file, 'wb'))

        return filename

    def process_mapping(self, update):
        if update.message.reply_to_message and update.message.reply_to_message.message_id in self.connect_request:
            try:
                [server_name, channel_name] = update.message.text.rsplit(": ", 1)
                reply_hide = twx.botapi.ReplyKeyboardHide.create()
                self.twx.send_message(update.message.chat.id, "IRC Channel not found, please connect", reply_markup=reply_hide)
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

            reply_markup = twx.botapi.ReplyKeyboardMarkup.create(self.build_keyboard(channels), one_time_keyboard=True, selective=True)
            request = self.twx.send_message(update.message.chat.id, "IRC Channel not found, please connect", reply_markup=reply_markup).join()
            self.connect_request[request.result.message_id] = update.message.chat.id

