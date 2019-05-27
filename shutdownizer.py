#!/usr/bin/python
#
# Copyright (C) 2019 Lukasz Kopacz
#
# This file is part of Shutdownizer.
#
# Shutdownizer is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Shutdownizer is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Shutdownizer. If not, see <http://www.gnu.org/licenses/>.


__version__ = "0.1"

import datetime
import argparse
import subprocess
import socket
import os
import traceback
import logging


shutdown_time_delay = 30  # delay time till shutdown in minutes
packet_length = 64  # length of one packet

paths = {
    'error_log': '.logs',
    'socket': '.sockets/shutdownizer_socket'  # UNIX socket location
}


def parsenizer():
    # Command line options
    parser = argparse.ArgumentParser(description='This program just shutdowns computer.')

    parser_group_type = parser.add_mutually_exclusive_group()
    parser_group_type.add_argument('-s', '--server', action='store_true', help='Starts server')

    parser_group_type.add_argument('-t', '--time', action='store_true', help='Shows shutdown time.')
    parser_group_type.add_argument('-r', '--remaining', action='store_true', help='Shows remaining time to shutdown.')
    parser_group_type.add_argument('-u', '--update', help='Extend or reduce time to shutdown.')
    parser_group_type.add_argument('-c', '--cancel', action='store_true', help='Cancels shutdown.')

    args = parser.parse_args()
    parameters = vars(args)

    return parameters


def prepend_message_length(msg):
    msg_len = str(len(msg.encode('utf-8')) + 6).zfill(6)
    return "{}{}".format(msg_len, msg)


def receive_data(conn, data):
    amount_expected = int(data.decode()[:6])
    amount_received = packet_length
    message = data.decode()[6:]
    while amount_received < amount_expected:
        data = conn.recv(packet_length)
        message += data.decode()
        amount_received += len(data)
    return message


def prepare_response(msg, t_shutdown, t_remaining):
    if msg == "remaining":
        return t_shutdown, str(t_remaining.total_seconds())
    elif msg == "time":
        return t_shutdown, str(t_shutdown)
    elif msg[:6] == "update":
        t_shutdown += datetime.timedelta(minutes=float(msg[6:]))
        return t_shutdown, str(t_shutdown)
    elif msg == "cancel":
        return t_shutdown, "-1"
    else:
        return t_shutdown, "Wrong query"


def shutdown_server():
    # Make sure the socket does not already exist
    try:
        os.unlink(paths['socket'])
    except OSError:
        if os.path.exists(paths['socket']):
            raise

    # Create a UDS socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    # Bind the socket to the address
    logging.info('Server: starting up on {}'.format(paths['socket']))
    sock.bind(paths['socket'])

    # Listen for incoming connections
    sock.listen(1)

    time_now = datetime.datetime.now()
    logging.info("Server: It is {}".format(time_now))
    time_shutdown = time_now + datetime.timedelta(minutes=shutdown_time_delay)
    logging.info("Server: Shutting down at {}, in {} minutes.".format(time_shutdown, shutdown_time_delay))

    while True:
        time_now = datetime.datetime.now()
        time_remaining = time_shutdown - time_now

        if time_remaining.total_seconds() < 0:
            return True

        sock.settimeout(time_remaining.total_seconds())
        logging.info("Server: Shutdown in {} seconds".format(sock.gettimeout()))

        try:
            # Wait for a connection
            logging.info('Server: waiting for a connection')
            connection, client_address = sock.accept()

            time_now = datetime.datetime.now()
            time_remaining = time_shutdown - time_now

            try:
                # Receive the data in small chunks and retransmit it
                while True:
                    first_data = connection.recv(packet_length)
                    if first_data:
                        incoming_message = receive_data(connection, first_data)

                        time_shutdown, response_message = prepare_response(incoming_message,
                                                                           time_shutdown,
                                                                           time_remaining)

                        back_data = prepend_message_length(response_message)
                        connection.sendall(back_data.encode('utf-8'))
                    else:
                        break
            finally:
                # Clean up the connection
                connection.close()
                if response_message == "-1":
                    logging.info('Server: Shutdown cancelled.')
                    return False

        except socket.timeout:
            return True


def shutdown_client(check_time, check_remaining, update_remaining, check_cancel):
    # Create a UDS socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    logging.info('Client: connecting to {}'.format(paths['socket']))
    try:
        sock.connect(paths['socket'])
    except socket.error as msg:
        return

    try:
        if check_remaining:
            message = "remaining"
        elif check_time:
            message = "time"
        elif update_remaining:
            message = 'update{}'.format(update_remaining)
        elif check_cancel:
            message = "cancel"
        else:
            message = 'This is the message.' \

        message = prepend_message_length(message)
        logging.info('Client: sending {!r}'.format(message))
        sock.sendall(message.encode('utf-8'))

        data = sock.recv(packet_length)

        incoming_message = receive_data(sock, data)

        logging.info('Client: received: {}'.format(incoming_message))

    finally:
        logging.info('Client: closing socket')
        sock.close()
        return incoming_message


def execute_shutdown():
    logging.info('Server: Executing shutdown.')

    # executing shutdown command
    command = "systemctl poweroff"
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()  # receive output


if __name__ == "__main__":
    logging.basicConfig(
                        level=logging.ERROR,
                        format='%(asctime)s %(levelname)s %(name)s %(message)s',
                        handlers=[logging.FileHandler(os.path.join(paths['error_log'], 'shutdownizer.log')),
                                  logging.StreamHandler()]
                        )
    logger = logging.getLogger(__name__)

    try:

        parser_par = parsenizer()
        if parser_par['server']:
            if shutdown_server():
                execute_shutdown()
        else:
            shutdown_client(parser_par['time'], parser_par['remaining'], parser_par['update'], parser_par['cancel'])

    except Exception as err:
        logger.error(traceback.format_exc())
