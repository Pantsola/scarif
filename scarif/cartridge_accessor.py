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

"""Classes for controlling head and picker devices from python"""
import logging

from serial import Serial
from .rail_control import XYGrblMotion

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)


class SoftLimitExceededException(Exception):
    """A soft limit has been exceeded"""
    pass


class Head(XYGrblMotion):
    """A class with methods for moving a tape library head along x and y axes.

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

    Raises
    ------
    SoftLimitExceededException: A defined soft limit was exceeded.
    """
    def __init__(self, port, baudrate, timeout,
                 accel_h, accel_v, x_limits, y_limits):
        super(Head, self).__init__(port, baudrate, timeout)
        self.accel_h = accel_h  # mm per min
        self.accel_v = accel_v  # mm per min
        self.x_limits = x_limits  # soft limits
        self.y_limits = y_limits  # soft limits

    def _set_horizontal_acceleration(self, mm_min):
        self.grbl_ctrl._command('$110=%i' % (mm_min))

    def _set_vertical_acceleration(self, mm_min):
        self.grbl_ctrl._command('$111=%i' % (mm_min))

    def configure(self):
        """Set kill alarm loc and make sure stepper motors are always on"""
        self.kill_alarm_lock()
        self.stepper_motors_always_on()

    def goto_x_y(self, x, y):
        """Check for soft limits before calling synchronous method for moving
        the head.

        Parameters
        ----------
        x : string float of x coordinates
        y : string float of y coordinates

        Returns
        -------
        Method from inherited class
        """
        if not float(self.x_limits[0]) <= float(x) <= float(self.x_limits[1]):
            raise SoftLimitExceededException('%s out of range [%s %s]' % (
                x, self.x_limits[0], self.x_limits[1]))
        if not float(self.y_limits[0]) <= float(y) <= float(self.y_limits[1]):
            raise SoftLimitExceededException('%s out of range [%s %s]' % (
                y, self.y_limits[0], self.y_limits[1]))
        return super(Head, self).goto_x_y(x, y)

    # movement methods
    def up(self, count):
        self._set_vertical_acceleration(self.accel_v)
        curr_stat = self.current_status()
        x_new = float(curr_stat['w_pos'][0]) + count
        self.goto_x_y('%.3f' % (x_new), curr_stat['w_pos'][1])

    def left(self, count):
        self._set_horizontal_acceleration(self.accel_h)
        curr_stat = self.current_status()
        y_new = float(curr_stat['w_pos'][1]) + count
        self.goto_x_y(curr_stat['w_pos'][0], '%.3f' % (y_new))

    def down(self, count):
        self.up(-1*count)

    def right(self, count):
        self.left(-1*count)


class Picker(object):
    """A class with methods for controlling a tape library picker. Three
    methods are implemented:
        * insert - move a tape from the picker to a slot/drive
        * retrieve - move a tape from a slot/drive to the picker
        * home - reset the picker - not elegant, but gets the job done

    Parameters
    ----------
    port: string: USB serial device to connect to, e.g. /dev/serial
    baudrate: integer : communications bit rate, e.g. 115200
    timeout: integer : USB serial communcations timeout in seconds
    """
    def __init__(self, port, baudrate, timeout):
        super(Picker, self).__init__()
        self._serial = Serial()
        self._serial.port = port
        self._serial.baudrate = baudrate
        self._serial.timeout = timeout
        self.open()

    def open(self):
        """Open the USB serial port to the arduino."""
        self._serial.open()

    def close(self):
        """Close the USB serial port to the arduino."""
        self._serial.close()

    def configure(self):
        """Configure the picker. Currently does nothing."""
        pass

    def insert(self):
        """Execute an insert sequence on the picker arduino."""
        self._serial.write("i")
        while True:
            data = self._serial.readline()
            if data:
                logger.debug(data.rstrip('\n'))
                if data.startswith('end'):
                    break

    def retrieve(self):
        """Execute a retrieve sequence on the picker arduino."""
        self._serial.write("r")
        while True:
            data = self._serial.readline()
            if data:
                logger.debug(data.rstrip('\n'))
                if data.startswith('end'):
                    break

    def home(self):
        """Execute a home sequence on the picker arduino."""
        self._serial.write("h")
        while True:
            data = self._serial.readline()
            if data:
                logger.debug(data.rstrip('\n'))
                if data.startswith('end'):
                    break
