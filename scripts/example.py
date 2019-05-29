#!/usr/bin/env python3

###############################################################################
# Copyright (c) 2019, National Research Foundation (Square Kilometre Array)
#
# Licensed under the BSD 3-Clause License (the "License"); you may not use
# this file except in compliance with the License. You may obtain a copy
# of the License at
#
#   https://opensource.org/licenses/BSD-3-Clause
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###############################################################################


from scarif import Head
from scarif import Picker as RobotPicker


H_CONF = {}
H_CONF['port'] = '/dev/cu.usbserial-XCONTROLLER1J4O4H'
H_CONF['baudrate'] = 115200
H_CONF['timeout'] = 5
H_CONF['accel_h'] = 8000  # mm per min
H_CONF['accel_v'] = 8000  # mm per min
H_CONF['x_limits'] = ['38.100', '770.0']
H_CONF['y_limits'] = ['12.700', '875.0']

P_CONF = {}
P_CONF['port'] = '/dev/cu.usbmodem1451'
P_CONF['baudrate'] = 9600
P_CONF['timeout'] = 0.1


class RobotHead(Head):
    """A class with methods for moving a tape library to preallocated positions.

    Parameters
    ----------
    port: string: USB serial device to connect to, e.g. /dev/serial
    baudrate: integer : communications bit rate, e.g. 115200
    timeout: integer : USB serial communcations timeout in seconds
    accel_h : integer : horizontal acceleration in mm per min
    accel_v : integer : vertical acceleration in mm per min
    x_limits : list of str floats : set the soft limits for x axis
        e.g. ['1.700, '1000.000']
    y_limits : list of str floats : set the sof limits for y axis
        e.g. ['0.000', '100.000']
    """
    def __init__(self, port, baudrate, timeout,
                 accel_h, accel_v, x_limits, y_limits):
        super(RobotHead, self).__init__(port, baudrate, timeout,
                                        accel_h, accel_v, x_limits, y_limits)

    # postion methods
    def home(self):
        current_status = {
            'm_pos': ['0.000', '0.000'],
            'state': 'Idle',
            'w_pos': ['38.100', '12.700']}
        xy = current_status['w_pos']
        self.goto_x_y(*xy)

    def slot1(self):
        current_status = {
            'm_pos': ['200.000', '200.000'],
            'state': 'Idle',
            'w_pos': ['238.100', '212.700']}
        xy = current_status['w_pos']
        self.goto_x_y(*xy)

    def slot2(self):
        current_status = {
            'm_pos': ['610.500', '600.000'],
            'state': 'Idle',
            'w_pos': ['648.600', '612.700']}
        xy = current_status['w_pos']
        self.goto_x_y(*xy)


class ExampleController(object):
    def __init__(self):
        self.head = RobotHead(**H_CONF)
        self.picker = RobotPicker(**P_CONF)

    def configure(self):
        self.head.configure()
        self.picker.configure()

    def run(self):
        # --- movement N test ---- #
        self.head.home()

        # start for N = 1
        self.head.slot1()
        self.picker.retrieve()
        self.head.home()
        self.picker.insert()
        # delay
        self.picker.retrieve()
        self.head.slot1()
        self.picker.insert()
        # end for N = 1

        # start for N = 2
        self.head.slot2()
        self.picker.retrieve()
        self.head.home()
        self.picker.insert()
        # delay
        self.picker.retrieve()
        self.head.slot2()
        self.picker.insert()
        # end for N = 2

        self.head.home()


if __name__ == "__main__":
    controller = ExampleController()
    controller.configure()
    controller.run()
