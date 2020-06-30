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

        self.devices = {
            "bb543900" : device("train", "netlin juna"),
            "886e8000" : device("hopper", "kaljaaaaa"),
            "deadbeef" : device("hopper", "jallua"),
            "94b91400" : device("switch", "Testi vaihde"),
        }

    def add_device(self, uid, func, name):
        self.devices.update({uid: device(func,name)})

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
        log.debug(topic, msg)
        self.mqtt.publish(topic, msg)

    def send_msgs(self, topic_list, msg):
        for topic in topic_list:
            self.send_msg(topic, msg)

    def _wait_msg(self, topic, timeout=1):
        reply = ""
        done = False
        def __wait_callback(client, userdata, message):
            nonlocal reply, done
            reply = message.payload
            done = True

        self.mqtt.subscribe(topic)
        self.mqtt.message_callback_add(topic, __wait_callback)

        while not done:
            time.sleep(0.02)
            timeout -= 0.02
            if timeout < 0:
                raise TimeoutError()

        self.mqtt.unsubscribe(topic)
        return reply.decode()

    def sub(self, uid, name, topic, callback):
        t = f"{uid}/{name}/{topic}"
        self.mqtt.subscribe(t)
        self.mqtt.message_callback_add(t, callback)

    def send_and_wait_list(self, topic_list, msg, resp_topic_list, timeout=1):
        response = []
        for a in zip(topic_list, resp_topic_list):
            self.send_msg(a[0], msg)
            response.append(self._wait_msg(a[1], timeout))
        return response

    def send_and_wait(self, topic, msg, resp_topic, timeout=1):
        self.send_msg(topic, msg)
        return self._wait_msg(resp_topic, timeout)
