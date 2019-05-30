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

"""Convenience classes for sending Grbl over a serial port from python"""
import re
import logging
import time

from serial import Serial
from collections import OrderedDict


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)


class GrblSerialException(Exception):
    """Grbl serial communications error"""
    pass


class GrblTimeoutException(Exception):
    """A grbl timeout on sending a command"""
    pass


class GrblCommandException(Exception):
    """A grbl command error"""
    pass


class GrblMotionModeExeption(Exception):
    """A grbl motion command exception"""
    pass


class GrblCtrl(object):
    """Low level abstraction of grbl commands as class methods

    Parameters
    ----------
    port : string : USB serial device to connect to, e.g. /dev/serial
    baudrate: integer : communications bit rate, e.g. 115200
    timeout: integer : USB serial communcations timeout in seconds

    Raises
    ------
    GrblSerialException: The serial port is not open
    GrblCommandException: Basic command checking before sending
    """
    def __init__(self, port, baudrate, timeout):
        super(GrblCtrl, self).__init__()
        self._serial = Serial()
        self._serial.port = port
        self._serial.baudrate = baudrate
        self._serial.timeout = timeout

    def open(self):
        self._serial.open()

    def close(self):
        self._serial.close()

    def _command(self, command):
        """Wrapper for executing a grbl command"""
        if not self._serial.isOpen():
            raise GrblSerialException('%s port is not open' % (self.port))
        result = self._serial.write(command+'\n')
        logger.debug('cmd: "%s" ret %i' % (command, result))
        return self._response()

    def _response(self):
        """Wrapper for grbl command response"""
        result = []
        logger.debug('res:')
        done = False
        while not done:
            raw_result = self._serial.readline()
            logger.debug(repr(raw_result))
            if raw_result == '':
                # TODO: Might be better to raise GrblTimeoutException here,
                #       something like:
                # raise GrblTimeoutException(
                #     'Timeout encountered on read.')
                logger.warning('Timeout encountered on read.')
                done = True
            if raw_result == 'ok\r\n':
                done = True
            result.append(raw_result.strip())
        return result

    # The '$'-commands are Grbl system commands used to tweak the settings,
    # view or change Grbl's states and running modes, and start a homing cycle.

    def _system_command(self, x):
        if not x.startswith('$'):
            raise GrblCommandException(
                '%s does not start with $' % (x))
        return self._command(x)

    def _g_command(self, x):
        if not x.startswith('G'):
            raise GrblCommandException(
                '%s does not start with G' % (x))
        return self._command(x)

    def view_grbl_settings(self):
        """$$ (view Grbl settings)"""
        return self._system_command('$$')

    def view_hash_parameters(self):
        """$# (view # parameters)"""
        return self._system_command('$#')

    def view_parser_state(self):
        """$G (view parser state)"""
        return self._system_command('$G')

    def view_build_info(self):
        """$I (view build info)"""
        return self._system_command('$I')

    def view_startup_blocks(self):
        """$N (view startup blocks)"""
        return self._system_command('$N')

    def save_grbl_setting(self, x, value):
        """$x=value (save Grbl setting)"""
        return self._system_command('${}={}'.format(x, value))

    def save_startup_block(self, x, line):
        """$Nx=line (save startup block)"""
        return self._system_command('$N{}={}'.format(x, line))

    def check_gcode_mode(self):
        """$C (check gcode mode)"""
        return self._system_command('$C')

    def run_homing_cycle(self):
        """$H (run homing cycle)"""
        try:
            return self._system_command('$H')
        except GrblTimeoutException:
            logger.warning('Expected timeout on command')

    # The non-'$' commands are realtime control commands that can be sent at
    # anytime, no matter what Grbl is doing. These either immediately change
    # Grbl's running behavior or immediately print a report of the important
    # realtime data like current position (aka DRO).

    def cycle_start(self):
        """~ (cycle start)"""
        return self._command('~')

    def feed_hold(self):
        """! (feed hold)"""
        try:
            return self._command('!')
        except GrblTimeoutException:
            logger.warning('Expected timeout on command')

    def current_status(self):
        """? (current status)"""
        return self._command('?')

    def reset_grbl(self):
        """ctrl-x (reset Grbl)"""
        return self._command('\x18')


class XYGrblMotion(object):
    """Low level abstraction of x and y motion for grbl commands
    as class methods.
    No z motion.

    Parameters
    ----------
    port: USB serial device to connect to, e.g. /dev/serial
    baudrate: communications bit rate, e.g. 115200
    timeout: USB serial communcations timeout in seconds

    Raises
    ------
    GrblMotionModeExeption: if state does not go back to 'Idle' or
    if an unsupported motion 'G' mode is set.
    """
    def __init__(self, port, baudrate, timeout):
        super(XYGrblMotion, self).__init__()
        self.grbl_ctrl = GrblCtrl(port, baudrate, timeout)
        self.grbl_ctrl.open()

    def current_status(self):
        state_re = r'Idle|Run|Hold|Door|Home|Alarm|Check'
        m_pos_re = r'MPos\:[-+]?\d*\.\d+,[-+]?\d*\.\d+,[-+]?\d*\.\d+'
        w_pos_re = r'WPos\:[-+]?\d*\.\d+,[-+]?\d*\.\d+,[-+]?\d*\.\d+'
        current_status = {}
        current_status['state'] = 'Unknown'
        current_status['m_pos'] = ['Unknown', 'Unknown']
        current_status['w_pos'] = ['Unknown', 'Unknown']
        result = self.grbl_ctrl.current_status()
        for r in result:
            if r.startswith('<') and r.endswith('>'):
                current_status['state'] = re.findall(
                    state_re, r)[0]
                current_status['m_pos'] = re.findall(
                    m_pos_re, r)[0].split(':')[1].split(',')[0:2]
                current_status['w_pos'] = re.findall(
                    w_pos_re, r)[0].split(':')[1].split(',')[0:2]
                break
        return current_status

    def kill_alarm_lock(self):
        """$X (kill alarm lock)"""
        return self.grbl_ctrl._system_command('$X')

    def stepper_motors_always_on(self):
        """$1=255 (stepper motor always on)"""
        return self.grbl_ctrl._system_command('$1=255')

    def stepper_motors_sleep(self):
        """$1=0 (stepper motor sleep)"""
        return self.grbl_ctrl._system_command('$1=0')

    def goto_x_y(self, x, y, motion_mode='G0'):
        """Syncronous call to goto x, y coords provided. Loop until done.
        A wrapper around the async_goto_x_y forcing wait until done.

        Parameters
        ----------
        x : string float of x coordinates
        y : string float of y coordinates
        motion_mode : grbl motion command, default is G0

        Returns
        -------
        None
        """
        self.async_goto_x_y(x, y, motion_mode)
        done = False
        while not done:
            curr_stat = self.current_status()
            state = curr_stat['state']
            x_cur, y_cur = curr_stat['w_pos']
            x_diff = float(x) - float(x_cur)
            y_diff = float(y) - float(y_cur)
            logger.debug('x == %s (%f), y == %s (%f)' % (
                x_cur, x_diff, y_cur, y_diff))
            if state == 'Idle' and x_diff == 0.0 and y_diff == 0.0:
                done = True
            else:
                time.sleep(0.5)

    def async_goto_x_y(self, x, y, motion_mode='G0'):
        """Asyncronous call to goto the x, y coords provided.
        A seperate call to the current_status() method will be
        required to find when the actual position reaches the
        desired position.

        Parameters
        ----------
        x : string float of x coordinates
        y : string float of y coordinates
        motion_mode : grbl motion command, default is G0

        Returns
        -------
        None
        """
        curr_stat = self.current_status()
        if curr_stat['state'] != 'Idle':
            raise GrblMotionModeExeption(
                'State is %s and not Idle.' % (self.state))
        if motion_mode in ['G0']:
            self.x_req = float(x)
            self.y_req = float(y)
            command = '%s X%s Y%s' % (
                motion_mode, '%.3f' % self.x_req, '%.3f' % self.y_req)
            res = self.grbl_ctrl._g_command(command)
            logger.debug('command:%s' % command)
            logger.debug('res:%s' % str(res))
        elif motion_mode in ['G1', 'G2', 'G3',
                             'G38.2', 'G38.3', 'G38.4', 'G38.5',
                             'G80']:
            raise GrblMotionModeExeption(
                '%s not implemented yet.' % (motion_mode))
            # G1 moves at the speed given by the F parameter and
            #    is called "feed"
            # G2 and G3 draw arcs, clockwise and counterclockwise
            # http://www.shapeoko.com/wiki/index.php/G-Code
        else:
            raise GrblMotionModeExeption(
                '%s not a valid motion mode.' % (motion_mode))

    def cycle_start(self):
        """This is the cycle start or resume command that can be issued at any
        time, as it is a real-time command. When a feed hold is executed, cycle
        start will resume the program.
        """
        return self.grbl_ctrl.cycle_start()

    def feed_hold(self):
        """The feed hold command will bring the active cycle to a stop via
        a controlled deceleration, so as not to lose position. It is also
        real-time and may be activated at any time. Once finished or paused,
        Grbl will wait until a cycle start command is issued to resume the
        program.
        """
        return self.grbl_ctrl.feed_hold()


class GrblSettings(object):
    """Grbl settings abstraction class for importing and exporting grbl
    settings"""
    def __init__(self):
        super(GrblSettings, self).__init__()
        self._settings_map = {
            '$0': 'step pulse, usec',
            '$1': 'step idle delay, msec',
            '$2': 'step port invert mask:00000000',
            '$3': 'dir port invert mask:00000011',
            '$4': 'step enable invert, bool',
            '$5': 'limit pins invert, bool',
            '$6': 'probe pin invert, bool',
            '$10': 'status report mask:00000011',
            '$11': 'junction deviation, mm',
            '$12': 'arc tolerance, mm',
            '$13': 'report inches, bool',
            '$20': 'soft limits, bool',
            '$21': 'hard limits, bool',
            '$22': 'homing cycle, bool',
            '$23': 'homing dir invert mask:00000011',
            '$24': 'homing feed, mm/min',
            '$25': 'homing seek, mm/min',
            '$26': 'homing debounce, msec',
            '$27': 'homing pull-off, mm',
            '$100': 'x, step/mm',
            '$101': 'y, step/mm',
            '$102': 'z, step/mm',
            '$110': 'x max rate, mm/min',
            '$111': 'y max rate, mm/min',
            '$112': 'z max rate, mm/min',
            '$120': 'x accel, mm/sec^2',
            '$121': 'y accel, mm/sec^2',
            '$122': 'z accel, mm/sec^2',
            '$130': 'x max travel, mm',
            '$131': 'y max travel, mm',
            '$132': 'z max travel, mm'
        }

    def _parse_settings(self, settings_list):
        settings_dict = OrderedDict()
        for s in settings_list:
            if s.startswith('$'):
                k, v = re.findall(r'^\$\d+=\d+', s)[0].split('=')
                settings_dict[k] = v
        return settings_dict

    def _pretty_print_settings(self, settings_dict):
        lines = []
        for k, v in settings_dict.items():
            lines.append('%s=%s (%s)' % (k, v, self._settings_map[k]))
        return '\n'.join(lines)

    def get_settings_from_grbl(self, grbl):
        ret = grbl.view_grbl_settings()
        return self._parse_settings(ret)

    def save_settings_to_grbl(self, grbl, settings_dict):
        for k, v in settings_dict.items():
            grbl.save_grbl_setting(k.strip('$'), v)

    def get_settings_from_file(self, filename):
        with open(filename, 'r') as settingsfile:
            ret = settingsfile.readlines()
        return self._parse_settings(ret)

    def save_settings_to_file(self, filename, settings_dict):
        with open(filename, 'w') as settingsfile:
            settingsfile.write(self._pretty_print_settings(settings_dict))

    def pretty_print_settings(self, settings_dict):
        print(self._pretty_print_settings(settings_dict))

    def show_command_descriptions(self):
        lines = []
        for k, v in self._settings_map.items():
            lines.append('%4s : %s' % (k, v))
        print('\n'.join(sorted(lines)))
