#!/bin/env python3
# -*- coding:utf-8 -*-
"""
Simple network tool just like netcat
Author: LY    Written in Python
Version: v0.3
2018-10-10 23:09
"""

import sys
import signal
import socket
import argparse
import threading
import subprocess


class Netcat:
    def __init__(self, verbose=False):
        self.options = {}
        self.options["max_len"] = 4096
        self.verbose = verbose
        # store the connection
        self.connections = {"srv": None, "client": None}

    def run(self):
        # Get the arguments needed
        self.arg_parse()
        # Handle the signal
        signal.signal(signal.SIGINT, self.exit)
        signal.signal(signal.SIGTERM, self.exit)
        # Start a server or be a client
        if self.options["listen"]:
            self.server_loop()
        else:
            self.client_loop()

    def exit(self, signum, field):
        """ Do many stuff to exit the program """
        # A big fucking bug, there must have three argument!!!
        if self.connections["client"]:
            self.connections["client"].shutdown(socket.SHUT_RDWR)
            self.connections["client"].close()
        if self.connections["srv"]:
            self.connections["srv"].shutdown(socket.SHUT_RDWR)
            self.connections["srv"].close()
        sys.exit(0)

    def arg_parse(self):
        """ Get all arguments from command line """
        parser = argparse.ArgumentParser(
            description="A simple netcat write in python")
        parser.add_argument(
            '-t',
            '--target',
            type=str,
            required=True,
            help='Target to connect or address to bind')
        parser.add_argument(
            '-p',
            '--port',
            type=int,
            required=True,
            help='Port to connect or to bind')
        parser.add_argument(
            '-l',
            '--listen',
            action='store_true',
            default=False,
            help='To be a server')
        parser.add_argument(
            '-c',
            '--command',
            action='store_true',
            default=False,
            help=
            'Execute a shell command on this machine and send the result to others'
        )
        arg = parser.parse_args()
        self.options["target"] = arg.target
        self.options["port"] = arg.port
        self.options["listen"] = arg.listen
        self.options["command"] = arg.command

    def server_loop(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.options[
            "target"] = '0.0.0.0' if not self.options["target"] else self.options[
                "target"]
        try:
            server.bind((self.options["target"], self.options["port"]))
            server.listen(1)
            client_sock, addr = server.accept()
            # Add client to the pool
            self.connections["client"] = client_sock
            threading.Thread(
                target=self.general_receiver, args=(client_sock, )).start()
            threading.Thread(
                target=self.general_sender, args=(client_sock, )).start()
        except socket.gaierror as e:
            print("Can't bind to the address", str(e), file=sys.stderr)
            server.close()
        except OSError as e:
            print("Address alreary in use\n", str(e), file=sys.stderr)
        else:
            self.connections["srv"] = server

    def client_loop(self):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client.connect((self.options["target"], self.options["port"]))
            threading.Thread(
                target=self.general_receiver, args=(client, )).start()
            threading.Thread(
                target=self.general_sender, args=(client, )).start()
        except ConnectionRefusedError:
            print("Connection was refused!", file=sys.stderr)
            sys.exit(-1)
        else:
            self.connections["client"] = client

    def general_sender(self, sock):
        if not self.options["command"]:
            while True:
                content = input().encode()
                sock.send(content)

    def general_receiver(self, sock):
        while True:
            response = sock.recv(self.options["max_len"]).decode()
            # Connection interruption
            if not response:
                sys.exit(1)
            if self.options["command"]:
                sock.send(self.run_command(response))
            else:
                print(response)

    def run_command(self, command):
        """ Execute shell command on this machine """
        try:
            # check_output will return a byte seq when it's successful
            output = subprocess.check_output(
                command, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError:
            output = "Failed to execute command.\n".encode()
        return output


if __name__ == '__main__':
    nc = Netcat()
    nc.run()
