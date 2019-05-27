#!/usr/bin/python
#
# Copyright (C) 2019 Łukasz Kopacz
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

import PySimpleGUI as sg
import shutdownizer
import time
import subprocess
import os
import traceback
import logging


paths = {
    'error_log': '.logs'
}


def main():
    shutdown_time = "Computer will shutdown at: {}".format(shutdownizer.shutdown_client(True, False, False, False)[:-6])
    logging.info("Gui: {}".format(shutdown_time))

    # layout
    layout = [[sg.Text(shutdown_time, key='text_shutdown')],
              [sg.ReadButton('Extend', key='button_extend'),
               sg.InputText('30', size=(5, None), key='input_extend'),
               sg.Text('minutes.')],
              [sg.ReadButton('Confirm', key='button_confirm'), sg.ReadButton('Cancel Shutdown', key='button_cancel')]
              ]

    # create the window
    window = sg.Window('Shutdownizer').Layout(layout)

    # read the window
    while True:
        event, values = window.Read()
        logging.info("Gui: {}".format(values))

        if event is None or event == 'button_confirm':
            logging.info("Gui: Exiting Gui.")
            break
        elif event == "button_extend":
            logging.info("Gui: Extend button pressed.")
            try:
                float(values['input_extend'])
                shutdown_time = "Computer will shutdown at: {}".format(
                    shutdownizer.shutdown_client(False, False, values['input_extend'], False)[:-6]
                )
                logging.info("Gui: {}".format(shutdown_time))
                window.FindElement('text_shutdown').Update(value=shutdown_time)
            except ValueError:
                logging.info("Gui: Value not correct.")
        elif event == "button_cancel":
            logging.info("Gui: Cancel button pressed.")
            if int(shutdownizer.shutdown_client(False, False, False, True)) < 0:
                window.FindElement('text_shutdown').Update(value="Shutting down canceled.")
                break


if __name__ == "__main__":
    logging.basicConfig(
                        level=logging.ERROR,
                        format='%(asctime)s %(levelname)s %(name)s %(message)s',
                        handlers=[logging.FileHandler(os.path.join(paths['error_log'], 'shutdownizer-gui.log')),
                                  logging.StreamHandler()]
                        )
    logger = logging.getLogger(__name__)
    try:
        command = "/usr/bin/python shutdownizer.py -s"
        subprocess.Popen(command.split(), stdin=None, stdout=None, stderr=None)

        time.sleep(2)

        main()

    except Exception as err:
        logger.error(traceback.format_exc())

