import pyglet
from pyglet.gl import *
import os
from light_patterns.components.component import LightPattern, Move, Pose, ManualLightPattern

class LightPatternDisplay:

    lps = []
    update_funcs = []

    def __init__(self, screen=1, fps=False, function_generator=None):
        self.function_generator = function_generator
        self.logging = False
        self.running = False
        display = pyglet.canvas.get_display()
        screens = display.get_screens()
        self.window = pyglet.window.Window(fullscreen=True, screen=screens[screen])
        pyglet.gl.glClearColor(0,0,0,1)
        self.window.set_mouse_visible(False)
        if fps:
            self.fps_display = pyglet.window.FPSDisplay(window=self.window)
        else:
            self.fps_display = None
        self.batch = pyglet.graphics.Batch()

    def add_light_pattern(self,x=None,y=None,scale=0.3,open_gear=True, manual=False, colour='red', **kwargs):
        if x is None:
            x = self.window.width//2
        if y is None:
            y = self.window.height//2
        if colour == 'red':
            fn = 'assets/gear_open_red.png' if open_gear else 'assets/gear_red.png'
        else:
            fn = 'assets/gear_open.png' if open_gear else 'assets/gear.png'
        fn = os.path.join(os.path.split(__file__)[0], fn)
        if not os.path.exists(fn):
            raise FileNotFoundError(f'File {fn} not found')
        if manual:
            lp = ManualLightPattern(fn, self.window, self.batch, x=x, y=y, scale=scale, **kwargs)
        else:
            lp = LightPattern(fn,self.window, self.batch, x=x, y=y, scale=scale, **kwargs)
            if self.logging:
                lp.start_logging(self.log_folder,self.prefix)
        self.lps.append(lp)
        return lp

    def moving(self):
        moving = False
        for lp in self.lps:
            if lp.moves_submitted and lp.moving:
                moving = True
            elif not lp.moves_submitted:
                moving = True
        return moving


    def start_logging(self, log_folder, prefix):
        self.logging = True
        self.log_folder = log_folder
        self.prefix = prefix
        for lp in self.lps:
            lp.start_logging(log_folder, prefix)

    def draw(self):
        """
        Clears screen and then renders our list of objects
        :return:
        """
        self.window.clear()
        self.batch.draw()
        if self.fps_display:
            self.fps_display.draw()

    def update(self,time):
        moving = self.moving()
        if not moving:
            self.lps = []
            self.batch = pyglet.graphics.Batch()
            if self.function_generator is not None:
                self.function_generator.OFF()
        for lp in self.lps:
            lp.update(time)
            #self.window.close()
        for func in self.update_funcs:
            func(time)
        #print(self.lp.pose)

    def run(self):
        """
        This is the main method. This contains an embedded method
        :return:
        """

        @self.window.event
        def on_draw():
            self.draw()

        pyglet.clock.schedule_interval(self.update, 1 / 120.0)
        pyglet.app.run()


def test(lpdisplay:LightPatternDisplay, lp:LightPattern):
    from time import sleep
    #while not lpdisplay.running:
    sleep(5)
    poses = [lp.pose,Pose(300,100,0)]#,Pose(500,500,-90)]
    for start, goal in zip(poses[:-1],poses[1:]):
        move = Move(start=start, goal=goal, max_velocity_t=100, max_velocity_r=100, acceleration_t=10, acceleration_r=10)
        lp.move_to(move)

if __name__ == '__main__':
    from concurrent.futures import ThreadPoolExecutor
    from functools import partial

    folder = r'C:\Users\micro\Desktop\test'
    prefix = 'test'
    tp = ThreadPoolExecutor(1)
    lpdisplay = LightPatternDisplay(screen=1)
    lp = lpdisplay.add_light_pattern(100,100,open_gear=False)
    tp.submit(partial(test, lpdisplay, lp))
    lpdisplay.run()

