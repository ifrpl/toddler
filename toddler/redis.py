__author__ = 'michal'

from threading import Thread
import redis


class RedisListener(Thread):

    def __init__(self, redis_url, channels, log, promise, *args, **kwargs):
        """
        = Redis listener =

        To run it you need `redis_url`, list of channels in `channels`,
        logger instance in `log` and a `concurrent.futures.Future` instance for
        `promise`

        When connection to redis cannot be established or listener has been
        stopped then promise will be set to `True`.

        The additional args and kwargs will be passed to Thread that lies
        beneath this object

        Please inherit from this class and override the `work` method.

        :param redis_url:
        :type redis_url: str
        :param channels:
        :type channels: list
        :param log:
        :param log: logger
        :param promise:
        :type promise: concurrent.futures.Future
        :param args:
        :param kwargs:
        :return:
        """

        super(RedisListener, self).__init__(*args, **kwargs)

        self.log = log
        self._redis_url = redis_url
        self._channels = channels
        self.pubsub = None
        self.redis = None
        self._promise = promise

    def on_connect(self, connection):
        return

    def connect(self):
        self.redis = redis.from_url(self._redis_url)
        test = self.redis.echo("Crawler test")

        if test.decode("utf8") != "Crawler test":
            self.log.error("Cannot connect to redis server {}".format(
                self._redis_url
            ))
            return False

        self.pubsub = self.redis.pubsub()
        self.pubsub.subscribe(self._channels)

        self.on_connect(self.redis)

        return True

    def stop(self):
        self.pubsub.unsubscribe()

    def run(self):
        if not self.connect():
            self._promise.cancel()
            return False

        for item in self.pubsub.listen():
            try:
                if item['type'] == 'message':
                    self.work(item)
            except Exception as e:
                self.log.exception(e)

        self._promise.set_result(True)


    def work(self, item):

        raise NotImplementedError


class RedisPublisher(object):

    def __init__(self, redis_url):

        self.redis = redis.from_url(redis_url)

    def publish(self, *args, **kwargs):
        self.redis.publish(*args, **kwargs)
