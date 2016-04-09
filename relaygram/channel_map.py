import json


class ChannelMap:
    def __init__(self, filename):
        self.filename = filename
        self.mapping = {
            'tg': {},
            'irc': {},
        }

        self.reload()  # Seed data

    def reload(self):
        try:
            self.mapping = json.load(open(self.filename, 'r'))
        except FileNotFoundError:
            pass  # Just use our empty mapping

    def save(self):
        try:
            json.dump(self.mapping, open(self.filename, 'w'))
        except FileNotFoundError:
            pass  # Just use our empty mapping

    def get_dest(self, protocol, src):
        try:
            return self.mapping[protocol][str(src)]  # We store this in json, so all keys are strings
        except KeyError:
            return None

    def set_mapping(self, tg_id, dest):
        # TODO support more than IRC
        self.mapping["tg"][str(tg_id)] = str(dest)
        self.mapping["irc"][str(dest)] = str(tg_id)
        self.save()

