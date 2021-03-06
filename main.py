"""Kaljajuna CLI
Usage:
  main.py [options] [<command>]

Options:
  --file=<file>             Run commans form a line
  --mqtt=<ip>               MQTT ip [default: 10.0.0.10]   


"""

import sys
import shlex
import mqtt_wrap
import docopt
import time
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import NestedCompleter

mqtt = None
exit_program = False

def cmd_exit(params):
    global exit_program
    exit_program = True

def cmd_help(params):
    for i, v in commands.items():
        print(f"{i:16s} {v[1]}")

def cmd_echo(params):
    print(str(params))

def cmd_mqtt_sub(params):
    if len(params) != 1:
        print("Usage:\nsub <topic>")
        return

    print(f"Subscribing to topic: {params[0]} ")

def cmd_mqtt_unsub(params):
    if len(params) != 1:
        print("Usage:\nunsub <topic>\nunsub all")
        return

    if params[0] == "all":
        print(f"Unsubscribing from all topics")
    else:
        print(f"Unsubscribing from topic: {params[0]} ")

def cmd_mqtt_pub(params):
    if len(params) != 2:
        print("Usage:\npub <topic> [msg]")
        return

    print(f"Publishing '{params[1]}' to '{params[0]}'")
    mqtt.send_msgs([params[0]], params[1])

def cmd_list(params):
    for key, value in mqtt.devices.items():
        print(f"{key:12s} {value.func:10s} {value.name}")
            

def cmd_add_device(params):
    if len(params) != 3:
        print("Usage:\nadd <uid> <function> <name>")
        return
    
    mqtt.add_device(params[0], params[1], params[2])
    
def cmd_mqtt_ping(params):
    if len(params) != 1:
        print("Usage:\nping <uid>\nping all")
        return

    def ping(uid):
        try:
            mqtt.send_msg(f"{uid}/sys/ping", "")
            mqtt.wait_msg(f"{uid}/sys/pong")
            print(f"{uid} OK")
        except TimeoutError:
            print(f"{uid} Timeout")
        except KeyError:
            print(f"{uid} Unknown device")

    if params[0] == "all":
        for uid in mqtt.devices:
            ping(uid)
    else:
        ping(params[0])

def cmd_write_file(params):
    if len(params) != 3:
        print("Usage:\nwrite <uid> <local-file> <remote-file>")
        return

    def write_file(uid, local, remote):
        try:
            with open(local, "r") as f:
                data = f.read()

            mqtt.send_msg(f"{uid}/sys/file", remote)
            mqtt.send_msg(f"{uid}/sys/write", data)
            mqtt.wait_msg(f"{uid}/sys/resp")

            print(f"{uid} OK")
        except TimeoutError:
            print(f"{uid} Timeout")
        except KeyError:
            print(f"{uid} Unknown device")

    uid, local, remote = params
    write_file(uid, local, remote)


def cmd_read_file(params):
    if len(params) != 3:
        print("Usage:\nread <uid> <remote-file> <local-file>")
        return

    def read_file(uid, local, remote):
        try:
            mqtt.send_msg(f"{uid}/sys/file", remote)
            mqtt.send_msg(f"{uid}/sys/read", "")
            data = mqtt.wait_msg(f"{uid}/sys/resp")

            with open(local, "w") as f:
                f.write(data)

            print(f"{uid} OK")
        except TimeoutError:
            print(f"{uid} Timeout")
        except KeyError:
            print(f"{uid} Unknown device")

    uid, remote, local = params
    read_file(uid, local, remote)
  
def cmd_kaljaa(params):
    def move_train(train_uid, steps):
        mqtt.send_msg(f"{train_uid}/+/move", str(steps))
        mqtt.wait_msg(f"{train_uid}/+/status", timeout=20, msg_filter="stopped")

    #Find a train
    train_uid = "bb543900"

    #Find a hopper
    hopper_uid = "886e8000"
    
    #Find a route to hopper
    steps_to_hopper = 2
    
    #Goto hopper station
    print(f"Train moving to hopper {mqtt.get_device_name(hopper_uid)}")

    mqtt.send_msg(f"{train_uid}/+/speed", "-0.5")
    move_train(train_uid, steps_to_hopper)

    #move_train(train_uid, steps_to_hopper)

    #Dispense beer
    print(f"Dispensing beer on to train")
    mqtt.send_msg(f"{hopper_uid}/+/dispense", str(0))
    mqtt.wait_msg(f"{hopper_uid}/+/dispense", 20, "done")
    time.sleep(1)

    print(f"Train is delivering")
    #Find a route to destionation
    steps_to_destination = 2

    #Goto destination
    move_train(train_uid, steps_to_destination)

commands = {
    "help": (cmd_help, "Prints this help"),
    "exit": (cmd_exit, "Exits the program"),
    "pub":  (cmd_mqtt_pub, "Publish to MQTT topic"),
    "ping": (cmd_mqtt_ping, "Test connection to device"),
    "write": (cmd_write_file, "Write file to a device"),
    "read" : (cmd_read_file, "Read file from device"),
    "kaljaa" : (cmd_kaljaa, "Get a beer"),
    "add" : (cmd_add_device, "Add temporary device ID"),
    "list": (cmd_list, "List all devices"),
}

def run_commad(cmd):
    if cmd == "":
        return 

    params = shlex.split(cmd)
    try:
        commands[params[0]][0](params[1:])
    except KeyError:
        print(f"Command not found: {cmd}")

def get_completer():

    topics = {f"{k}":None for (k,v) in mqtt.devices.items()}
    topics_long = {f"{k}/{v.func}/":None for (k,v) in mqtt.devices.items()}

    completer = NestedCompleter.from_nested_dict({
        "help" : None,
        "exit" : None,
        "pub" : topics_long,
        "ping" : {**{"all":None}, **topics},
        "write" : topics,
        "read" : topics,
        "add" : None,
        "list" : None,
        "kaljaa" : None,
    })

    return completer

if __name__ == "__main__":
    args = docopt.docopt(__doc__)
    print(args)

    #mqtt = mqtt_wrap.mqtt("localhost")
    mqtt = mqtt_wrap.mqtt(args["--mqtt"])

    if args["<command>"]:
        print(f"Running command {args['<command>']}")
        run_commad(args["<command>"])

    else:
        p = PromptSession(
            history=FileHistory('./kaljajuna_cli_history.txt'),
            completer=get_completer(),
            )

        while not exit_program:
            cmd = p.prompt("> ")
            run_commad(cmd)

    print("Bye")

