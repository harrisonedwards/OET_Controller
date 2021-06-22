from math import sqrt, pi, degrees
from collections import deque
from dataclasses import dataclass
import pyglet
from logs import LogWriter
import os
from itertools import count
from timeit import default_timer as timer
import math
import numpy as np

@dataclass
class Pose:
    x: float
    y: float
    rotation: float

    def __post_init__(self):
        if self.rotation<-180 or self.rotation>180:
            rotation = self.rotation%360
            if rotation >180:
                rotation = -(360-rotation)
            self.rotation = rotation
            #raise Exception(f'Invalid rotation for pose:{self.rotation}. Acceptable rotations between -180 and 180')

    @classmethod
    def from_radians(cls, x, y, r):
        if r < -pi or r > pi:
            raise Exception(f'Invalid rotation for pose:{r}. Acceptable rotations between -pi and pi')
        r = min(max(degrees(r), -180), 180)
        if r == -180:
            r = 180
        return cls(x, y, r)

    @classmethod
    def from_degrees(cls, x, y, r):
        if r < -180 or r > 180:
            raise Exception(f'Invalid rotation for pose:{r}. Acceptable rotations between -180 and 180')

        return cls(x, y, r)

    def at_location(self, pose, direction):
        direction_x, direction_y = direction

        if direction_x == 1:
            at_x = pose.x <= self.x
        else:
            at_x = pose.x >= self.x

        if direction_y == 1:
            at_y = pose.y <= self.y
        else:
            at_y = pose.y >= self.y

        return at_x and at_y

    def at_rotation(self, pose, direction):
        if direction == 1:
            return pose.rotation <= self.rotation
        else:
            return pose.rotation >= self.rotation


@dataclass
class Move:
    start: Pose
    goal: Pose
    max_velocity_t: float
    max_velocity_r: float
    acceleration_t: float
    acceleration_r: float

    def __post_init__(self):
        self.start = Pose(self.start.x, self.start.y, self.start.rotation)
        self.goal = Pose(self.goal.x, self.goal.y, self.goal.rotation)
        self.t = -1
        self.finished = False
        self.total_distance_x = self.goal.x - self.start.x
        self.total_distance_y = self.goal.y - self.start.y
        self.direction_t = (np.sign(self.total_distance_x),np.sign(self.total_distance_y))
        self.total_distance_t = sqrt((self.total_distance_x ** 2) + (self.total_distance_y ** 2))

        if self.acceleration_t > 0:
            self.max_velocity_distance_t = (self.max_velocity_t ** 2) / self.acceleration_t
        else:
            self.max_velocity_distance_t = 0

        self.total_distance_r = self.goal.rotation - self.start.rotation
        if self.total_distance_r > 180:
            self.total_distance_r -= 360
        elif self.total_distance_r < -180:
            self.total_distance_r += 360

        self.direction_r = np.sign(self.total_distance_r)

        if self.acceleration_r > 0:
            self.max_velocity_distance_r = (self.max_velocity_r ** 2) / self.acceleration_r
        else:
            self.max_velocity_distance_r = 0

    def displacement_constant(self, acceleration, max_velocity, max_velocity_distance, total_distance):
        """
        Total displacement after "t" time given constant acceleration, slowing to 0 velocity at goal

        :param t: time since start of move (seconds)
        :param acceleration:
        :param max_velocity:
        :param max_velocity_distance:
        :param total_distance:
        :return: displacement as %
        """
        total_distance = abs(total_distance)
        if total_distance <= max_velocity_distance:
            v_max = sqrt(total_distance * acceleration)
            total_time = 2 * (v_max / acceleration)

            if self.t <= total_time / 2:
                return (0.5 * acceleration * (self.t ** 2)) / total_distance
            elif self.t < total_time:
                return (total_distance - (acceleration * ((total_time - self.t) ** 2)) / 2) / total_distance
            else:
                return 1
        else:
            t1 = max_velocity / acceleration
            if self.t < t1:
                return (0.5 * acceleration * (self.t ** 2)) / total_distance

            t2 = t1+(total_distance-(max_velocity*t1))/max_velocity
            total_time = t1 + t2
            if t1 <= self.t <= t2:
                return (((t1 * max_velocity) / 2) + (self.t - t1) * max_velocity) / total_distance
            elif self.t < total_time:
                return (((max_velocity * (2 * t2)) - (acceleration * (total_time - self.t) ** 2)) / 2) / total_distance
            else:
                return 1

    def translation(self):

        if self.acceleration_t > 0:
            displacement = self.displacement_constant(self.acceleration_t, self.max_velocity_t,
                                                      self.max_velocity_distance_t, self.total_distance_t)
        else:
            displacement = (self.max_velocity_t * self.t) / self.total_distance_t
        x = self.start.x + (self.total_distance_x * displacement)
        y = self.start.y + (self.total_distance_y * displacement)
        return x, y

    def rotation(self, t):

        if self.acceleration_r > 0:
            displacement = self.displacement_constant(self.acceleration_r, self.max_velocity_r,
                                                      self.max_velocity_distance_r, self.total_distance_r)
        else:
            displacement = (self.max_velocity_r * t) / self.total_distance_r
        r = self.start.rotation + (self.total_distance_r * displacement)
        return r

    def update(self, dt, pose):
        if self.t < 0:
            self.t = 0
        else:
            self.t += dt
        moved = False
        if not pose.at_location(self.goal,self.direction_t):
            x, y = self.translation()
            moved = True
        else:
            x, y = pose.x, pose.y
        if not pose.at_rotation(self.goal,self.direction_r):
            r = self.rotation(self.t)
            moved = True
        else:
            r = pose.rotation
        #print(self.t, x, (x - pose.x) /dt)
        pose.x = x
        pose.y = y
        pose.rotation = r
        if not moved:
            self.finished = True
        print(pose)
        return pose


class Component():

    _ids = count(0)

    def __init__(self, *args, **kwargs):
        """
        Constructs Component object given passed kwargs.

        :param active Defines if the object has to update
        :param render Defines if the object has to render
        :param x Defines the x location of the object
        :param y Defines the y location of the object
        :param width Defines the width of the object
        :param height Defines the height of the object
        """
        self.id = next(self._ids)
        # Basic stuff
        self.t = 0.0
        self.active = kwargs.get('active', True)
        self.render = kwargs.get('render', True)
        self.debug = kwargs.get('debug', False)
        x = kwargs.get('x', 0.0)
        y = kwargs.get('y', 0.0)
        rotation = kwargs.get('rotation', 0.0)
        self.pose = Pose(x, y, rotation)
        self.width = kwargs.get('width', 0)
        self.height = kwargs.get('height', 0)
        self.move_q = deque()
        self.moves_submitted = False
        self.moving = False

    def move_to(self, move: Move, interrupt=False):
        if interrupt:
            self.move_q.clear()
        self.move_q.appendleft(move)

    def update(self, dt):
        self.t += dt
        if len(self.move_q) == 0:
            self.moving = False
            return
        self.moves_submitted = True
        self.moving = True
        move = self.move_q[-1]
        move.update(dt, self.pose)
        if move.finished:
            self.move_q.pop()



class LightPattern(Component):

    def __init__(self, image, window, batch, *args, **kwargs):
        """
        Creates a sprite using an image.
        """
        super(LightPattern, self).__init__(*args, **kwargs)
        self.logging = False
        self.image = pyglet.image.load(image)
        self.image.anchor_x = self.image.width // 2
        self.image.anchor_y = self.image.height // 2
        self.window = window
        self.width = self.image.width
        self.height = self.image.height
        self.sprite = pyglet.sprite.Sprite(self.image, self.pose.x, self.pose.y, batch=batch)
        self.sprite.scale = kwargs.get('scale', 1)

    def start_logging(self,log_folder, prefix):
        if not self.logging:
            self.log = LogWriter(os.path.join(log_folder, f'{prefix}_lp{self.id}.log'))
            self.logging = True

    def update(self, dt):
        super(LightPattern, self).update(dt)

        # if self.pose.x < self.sprite.width / 2:
        #     self.pose.x = self.sprite.width / 2
        # elif (self.pose.x + self.sprite.width / 2) > self.window.width:
        #     self.pose.x = self.window.width - self.sprite.width / 2
        #
        # if self.pose.y < self.sprite.height / 2:
        #     self.pose.y = self.sprite.height / 2
        # elif (self.pose.y + self.sprite.height / 2) > self.window.height:
        #     self.pose.y = self.window.height - self.sprite.height / 2

        self.sprite.position = (self.pose.x, self.pose.y)
        self.sprite.rotation = self.pose.rotation
        if self.logging:
            self.log.write(timer(),self.pose.x,self.pose.y,self.pose.rotation)

    def toggle_display(self,on=None):
        if on is None:
            if self.sprite.opacity > 0:
                self.sprite.opacity = 0
            else:
                self.sprite.opacity = 255
        self.sprite = 255 if on else 0


class ManualLightPattern(LightPattern):
    EPS = 0.00001

    def __init__(self, image, window, batch, *args, **kwargs):
        """
        Creates a sprite using an image.
        """
        super(ManualLightPattern, self).__init__(image, window, batch, *args, **kwargs)
        self.speed = kwargs.get('speed', 5)
        self.rotation_rate = kwargs.get('rotation_rate', 0.2)


    def move_y(self, direction=1, cardinal=True):
        if cardinal:
            self.pose.y += self.speed * direction
        else:
            self.pose.y += math.cos(math.radians(self.sprite.rotation)) * self.speed * direction
            self.pose.x += math.sin(math.radians(self.sprite.rotation)) * self.speed * direction

    def move_x(self, direction=1, cardinal=True):
        if cardinal:
            self.pose.x += self.speed * direction
        else:
            self.pose.y += math.cos(math.radians(self.sprite.rotation - 90)) * self.speed * direction
            self.pose.x += math.sin(math.radians(self.sprite.rotation - 90)) * self.speed * direction

    def rotate(self, direction=1, dt=None):
        if dt is None:
            self.pose.rotation += self.rotation_rate * direction
        else:
            self.pose.rotation += dt * (math.degrees(self.rotation_rate) * direction)

    def set_rotation(self, rotation):
        self.sprite.rotation = rotation

    def grow(self, amount=0.01):
        self.sprite.scale += amount
        print(f"Scale: {self.sprite.scale:.2f}")

    def shrink(self, amount=0.01, log=True):
        if self.sprite.scale > amount + self.EPS:
            self.sprite.scale -= amount
            if log:
                print(f"Scale: {self.sprite.scale:.2f}")

    def faster(self, amount=0.1):
        self.speed += amount
        print(f'Speed: {self.speed:.2f}')

    def slower(self, amount=0.1):
        if self.speed > amount + self.EPS:
            self.speed -= amount
            print(f'Speed: {self.speed:.2f}')

    def rotate_faster(self, amount=0.05):
        self.rotation_rate += amount
        print(f'Speed: {self.rotation_rate:.3f}')

    def rotate_slower(self, amount=0.05):
        if self.rotation_rate > amount + self.EPS:
            self.rotation_rate -= amount
            print(f'Speed: {self.rotation_rate:.3f}')
