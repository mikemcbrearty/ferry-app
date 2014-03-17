import datetime
import json
import os

import psycopg2
import tornado.ioloop
import tornado.web
import tornado.websocket

from tornado.options import define, options, parse_command_line

define("port", default=8888, help="run on the given port", type=int)

ENV_VARS = {
    "FERRY_DBNAME": "dbname",
    "FERRY_DBUSER": "user",
    "FERRY_DBPWD": "password",
}
DB_CREDS = " ".join(ENV_VARS[var]+"="+os.environ[var] for var in ENV_VARS.keys() if var in os.environ)


class LocationsBuffer():
    def __init__(self):
        self.waiters = set()
        self.conn = psycopg2.connect(DB_CREDS)
        self.cur = self.conn.cursor()
        self.cache_size = 20
        dt = datetime.datetime(2014, 3, 14, 0, 0)
        self.cache = dict([mmsi, self.ferry_locations(mmsi, dt)] for mmsi in self.mmsi_list())
        self.callback = tornado.ioloop.PeriodicCallback(self.update_locations, 30000)
        self.callback.start()

    def mmsi_list(self):
        self.cur.execute("SELECT DISTINCT(mmsi) FROM locations;")
        return [row[0] for row in self.cur.fetchall()]

    def ferry_locations(self, mmsi, dt):
        cols = ["mmsi", "latitude", "longitude", "last_update"]
        self.cur.execute(
            """SELECT mmsi, latitude, longitude, last_update FROM locations
               WHERE mmsi=%s AND last_update>%s
               ORDER BY last_update DESC LIMIT %s;""",
               (mmsi, dt, self.cache_size))
        return [dict(zip(cols, row)) for row in self.cur.fetchall()]

    def wait(self, callback):
        self.waiters.add(callback)

    def cancel_wait(self, callback):
        self.waiters.remove(callback)

    def update_locations(self):
        for mmsi in self.cache.keys():
            dt = self.cache[mmsi][0]["last_update"]
            new_locations = self.ferry_locations(mmsi, dt)
            if new_locations:
                self.cache[mmsi] = (new_locations + self.cache[mmsi])[:self.cache_size]
                for callback in self.waiters:
                    try:
                        callback(new_locations)
                    except:
                        pass


locations_buffer = LocationsBuffer()


class DtEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        self.stream.set_nodelay(True)
        for locs in locations_buffer.cache.values():
            self.write_message(json.dumps(locs, cls=DtEncoder))
        locations_buffer.wait(self.on_new_locations)

    def on_message(self, message):
        pass

    def on_new_locations(self, locs):
        self.write_message( json.dumps(locs, cls=DtEncoder) )

    def on_close(self):
        locations_buffer.cancel_wait(self.on_new_locations)


app = tornado.web.Application([
    (r'/staten-island-ferry', WebSocketHandler),
])

if __name__ == '__main__':
    parse_command_line()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
