import sys
import time
import json
import traceback
from itertools import cycle
from threading import Thread
from ibquery import InfoBeamerQuery, InfoBeamerQueryException

class Client(Thread):
    def __init__(self, addr):
        super(Client, self).__init__()
        self._addr = addr
        self._state = "disconnected"
        self.daemon = True
        self.start()

    def run(self):
        while 1:
            try:
                self.reconnect()
            except InfoBeamerQueryException:
                time.sleep(0.2)
                continue

            try:
                while 1:
                    line = self._io.readline().strip()
                    if not line:
                        break
                    self._state = line
            except KeyboardInterrupt:
                break
            except Exception, err:
                print "something went wrong. reconnecting"
                self._state = "disconnected"
                traceback.print_exc()
                time.sleep(1)

    def reconnect(self):
        self._io = InfoBeamerQuery(self._addr).node("multiscreen").io(raw=True)

    def send(self, line):
        self._io.write(line + "\n")
        self._io.flush()
        self._state = "waiting for confirmation"

    @property
    def state(self):
        return self._state

def main(config_filename, playlist_filename, display_addrs):
    next_file = cycle(video.strip() for video in file(playlist_filename)).next
    config = json.load(file(config_filename))

    clients = []
    for screen_id, addr in enumerate(display_addrs):
        print "adding screen %d at %s" % (screen_id, addr)
        clients.append(Client(addr))

    def send_config(config):
        for screen_id, client in enumerate(clients):
            line = json.dumps({
                "cmd": "config",
                "screen_id": screen_id,
                "config": config,
            })
            client.send(line)

    def send_all(command, **options):
        options.update({"cmd": command})
        line = json.dumps(options)
        for client in clients:
            client.send(line)

    def all_in_any_of(states, *any_of):
        return all(state in any_of for state in states)

    def any_in_any_of(states, *any_of):
        return any(state in any_of for state in states)

    while 1:
        states = [client.state for client in clients]
        for addr, state in zip(display_addrs, states):
            print "%-30s %s" % (addr, repr(state))
        print

        if all_in_any_of(states, "none", "finished"):
            send_config(config)
            send_all("load", filename = next_file())
        elif all_in_any_of(states, "paused"):
            send_all("start")
        elif any_in_any_of(states, "error"):
            # any display failed? -> restart everything
            send_all("load", filename = next_file())

        time.sleep(0.1)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print "%s <screens.json> <playlist.txt> <addr-screen-0> [<addr-screen-1> ...]" % sys.argv[0]
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
