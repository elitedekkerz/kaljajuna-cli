import re
import sys
import time
import paho.mqtt.client
import logging

log = logging.getLogger("MQTT")

class device:
    def __init__(self, func, name):
        self.name = name
        self.func = func

class mqtt:
    def __init__(self, ip="localhost"):
        log.info("creating new instance")
        self.mqtt = paho.mqtt.client.Client() #create new instance
        log.info("connecting to broker")
        self.mqtt.connect(ip) #connect to broker
        log.info("Connected")
        self.mqtt.loop_start()

        self.devices = {}
        self.add_device("bb543900", "train", "netlin juna")
        self.add_device("886e8000", "hopper", "kaljaaaaa")
        self.add_device("94b91400", "switch", "Testi vaihde")
        self.add_device("deadbeef", "hopper", "jallua")

    def add_device(self, uid, func, name):
        self.devices.update({uid: device(func,name)})

    def get_device_name(self, uid):
        return self.devices[uid].name

    def _replace_topic_wildcards(self, topic):
        parts = topic.split("/")
        uid = parts[0]

        if len(parts) > 1 and parts[1] == "+":
            parts[1] = self.devices[uid].func

        return "/".join(parts)            

    def gen_topic_list(self, uid=None, name=None, topic=None):
        t = []
        topic = "/" + topic if topic else ""

        #If uid is empty send to all devices
        if uid == None:
            for key, value in self.devices.items():
                t.append(f"{key}/{value.func}{topic}")

        #If name is empty populate it automatically 
        elif name == None:
            t = [f"{uid}/{self.devices[uid].func}{topic}"]
        else:
            t = [f"{uid}/{name}{topic}"]

        return t

    def gen_topic(self, uid, name=None, topic=None):
        topic = "/" + topic if topic else ""

        #If name is empty populate it automatically 
        if name == None:
            return f"{uid}/{self.devices[uid].func}{topic}"
        else:
            return f"{uid}/{name}{topic}"

    def send_msg(self, topic, msg):
        topic = self._replace_topic_wildcards(topic)
        log.debug(topic, msg)
        self.mqtt.publish(topic, msg)

    def send_msgs(self, topic_list, msg):
        for topic in topic_list:
            self.send_msg(topic, msg)

    def wait_msg(self, topic, timeout=1, msg_filter=None):
        reply = ""
        done = False
        mf = re.compile(msg_filter) if msg_filter else None

        def __wait_callback(client, userdata, message):
            nonlocal reply, done, mf
            data = message.payload.decode()
            if mf is None:
                reply = data
                done = True
            elif mf.match(data):
                reply = data
                done = True

        topic = self._replace_topic_wildcards(topic)
        self.mqtt.subscribe(topic)
        self.mqtt.message_callback_add(topic, __wait_callback)

        while not done:
            time.sleep(0.02)
            timeout -= 0.02
            if timeout < 0:
                raise TimeoutError()

        self.mqtt.unsubscribe(topic)
        return reply

    def sub(self, uid, name, topic, callback):
        t = f"{uid}/{name}/{topic}"
        self.mqtt.subscribe(t)
        self.mqtt.message_callback_add(t, callback)

    def send_and_wait_list(self, topic_list, msg, resp_topic_list, timeout=1):
        response = []
        for a in zip(topic_list, resp_topic_list):
            self.send_msg(a[0], msg)
            response.append(self.wait_msg(a[1], timeout))
        return response
