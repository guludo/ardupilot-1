'''calibration simulation command handling'''

from __future__ import division, print_function
import math
from pymavlink import quaternion

from MAVProxy.modules.lib import mp_module

class CalController(object):
    def __init__(self, mpstate):
        self.mpstate = mpstate
        self.active = False
        self.reset()

    def reset(self):
        self.desired_quaternion = None
        self.general_state = 'idle'
        self.attitude_callback = None
        self.desired_quaternion_close_count = 0

    def start(self):
        self.active = True

    def stop(self):
        self.reset()
        self.mpstate.functions.process_stdin('servo set 5 1000')
        self.active = False

    def normalize_attitude_angle(self, angle):
        if angle < 0:
            angle = 2 * math.pi + angle % (-2 * math.pi)
        angle %= 2 * math.pi
        if angle > math.pi:
            return angle % -math.pi
        return angle

    def set_attitute(self, roll, pitch, yaw, callback=None):
        roll = self.normalize_attitude_angle(roll)
        pitch = self.normalize_attitude_angle(pitch)
        yaw = self.normalize_attitude_angle(yaw)

        self.desired_quaternion = quaternion.Quaternion((roll, pitch, yaw))
        self.desired_quaternion.normalize()

        scale = 500.0 / math.pi

        roll_pwm = 1500 + int(roll * scale)
        pitch_pwm = 1500 + int(pitch * scale)
        yaw_pwm = 1500 + int(yaw * scale)

        self.mpstate.functions.process_stdin('servo set 5 1150')
        self.mpstate.functions.process_stdin('servo set 6 %d' % roll_pwm)
        self.mpstate.functions.process_stdin('servo set 7 %d' % pitch_pwm)
        self.mpstate.functions.process_stdin('servo set 8 %d' % yaw_pwm)

        self.general_state = 'attitude'
        self.desired_quaternion_close_count = 0

        if callback:
            self.attitude_callback = callback

    def angvel(self, x, y, z, theta):
        m = max(abs(x), abs(y), abs(z))
        if not m:
            x_pwm = y_pwm = z_pwm = 1500
        else:
            x_pwm = 1500 + round((x / m) * 500)
            y_pwm = 1500 + round((y / m) * 500)
            z_pwm = 1500 + round((z / m) * 500)

        max_theta = 2 * math.pi
        if theta < 0:
            theta = 0
        elif theta > max_theta:
            theta = max_theta
        theta_pwm = 1200 + round((theta / max_theta) * 800)

        self.mpstate.functions.process_stdin('servo set 5 %d' % theta_pwm)
        self.mpstate.functions.process_stdin('servo set 6 %d' % x_pwm)
        self.mpstate.functions.process_stdin('servo set 7 %d' % y_pwm)
        self.mpstate.functions.process_stdin('servo set 8 %d' % z_pwm)

        self.general_state = 'angvel'

    def handle_simstate(self, m):
        if self.general_state == 'attitude':
            q = quaternion.Quaternion((m.roll, m.pitch, m.yaw))
            q.normalize()
            d1 = abs(self.desired_quaternion.q - q.q)
            d2 = abs(self.desired_quaternion.q + q.q)
            if (d1 <= 1e-2).all() or (d2 <= 1e-2).all():
                self.desired_quaternion_close_count += 1
            else:
                self.desired_quaternion_close_count = 0

            if self.desired_quaternion_close_count == 5:
                self.general_state = 'idle'
                if callable(self.attitude_callback):
                    self.attitude_callback()
                    self.attitude_callback = None

    def mavlink_packet(self, m):
        if not self.active:
            return
        if m.get_type() == 'SIMSTATE':
            self.handle_simstate(m)


class SitlCalibrationModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(SitlCalibrationModule, self).__init__(mpstate, "sitl_calibration")
        self.add_command(
            'sitl_attitude',
            self.cmd_sitl_attitude,
            'set the vehicle at the inclination given by ROLL, PITCH and YAW' +
            ' in degrees',
        )
        self.add_command(
            'sitl_angvel',
            self.cmd_angvel,
            'apply angular velocity on the vehicle with a rotation axis and a '+
            'magnitude in degrees/s',
        )
        self.add_command(
            'sitl_stop',
            self.cmd_sitl_stop,
            'stop the current calibration control',
        )

        self.controllers = dict(
            generic_controller=CalController(mpstate),
        )

        self.current_controller = None

    def set_controller(self, controller):
        if self.current_controller:
            self.current_controller.stop()

        controller = self.controllers.get(controller, None)
        if controller:
            controller.start()
        self.current_controller = controller

    def cmd_sitl_attitude(self, args):
        if len(args) != 3:
            print('Usage: sitl_attitude <ROLL> <PITCH> <YAW>')
            return

        try:
            roll, pitch, yaw = args
            roll = math.radians(float(roll))
            pitch = math.radians(float(pitch))
            yaw = math.radians(float(yaw))
        except ValueError:
            print('Invalid arguments')

        self.set_controller('generic_controller')
        self.current_controller.set_attitute(roll, pitch, yaw)

    def cmd_angvel(self, args):
        if len(args) != 4:
            print('Usage: sitl_angvel <AXIS_X> <AXIS_Y> <AXIS_Z> <THETA>')
            return

        try:
            x, y, z, theta = args
            x = float(x)
            y = float(y)
            z = float(z)
            theta = math.radians(float(theta))
        except ValueError:
            print('Invalid arguments')

        self.set_controller('generic_controller')
        self.current_controller.angvel(x, y, z, theta)

    def cmd_sitl_stop(self, args):
        self.set_controller('generic_controller')

    def mavlink_packet(self, m):
        for c in self.controllers.values():
            c.mavlink_packet(m)

def init(mpstate):
    '''initialise module'''
    return SitlCalibrationModule(mpstate)
