import pyglet
from addict import Dict
import atexit
import os
import confuse
from light_patterns.light_pattern_display import LightPatternDisplay

class KeyboardController():
    key = pyglet.window.key
    keys = {}
    controls = {}

    def __init__(self, lightpatterndisplay:LightPatternDisplay, config, stage=None, function_generator=None):
        self.lpd = lightpatterndisplay
        self.lpd.window.push_handlers(self)
        self.lpd.update_funcs.append(self.update)
        self.parse_controls(config)
        self.config = config
        transpose = config['settings']['transpose_controls'].get(bool)
        if transpose:
            self.transpose_controls()
        atexit.register(self.save_settings)
        self.toggle = True
        self.stage = stage
        self.stage_speed = self.config['settings']['stage_speed'].get()
        self.mirror_vertical()
        self.toggle_clockwise = False
        self.toggle_counter_clockwise = False
        self.function_generator = function_generator
    
    def transpose_controls(self):
        temp_up = self.controls.up
        self.controls.up = self.controls.left
        self.controls.left = temp_up
        
        temp_down = self.controls.down
        self.controls.down = self.controls.right
        self.controls.right = temp_down

    def mirror_vertical(self):
        temp_left = self.controls.left
        self.controls.left = self.controls.right
        self.controls.right = temp_left
    
    def save_settings(self):
        pattern = self.lpd.lps[0]
        print('Saving settings to', os.path.join(self.config.config_dir(), confuse.CONFIG_FILENAME))
        self.config['settings']['speed'].set(pattern.speed)
        self.config['settings']['scale'].set(pattern.sprite.scale)
        self.config['settings']['rotation_speed'].set(pattern.rotation_rate)
        self.config['settings']['stage_speed'].set(self.stage_speed)
        with open(os.path.join(self.config.config_dir(),
                               confuse.CONFIG_FILENAME), 'w') as f:
            f.write(self.config.dump())

    def parse_controls(self,controls):
        controls = Dict(controls['controllers'].get())
        if 'keyboard' in controls:
            self.controls = controls.keyboard.controls
        else:
            print('No keyboard controls found in configuration.')

    def on_key_press(self, symbol, modifiers):
        self.keys[symbol] = True
        self.toggle = True

    def on_key_release(self, symbol, modifiers):
        self.keys[symbol] = False

    def update(self,dt):
        for component in self.lpd.lps:
            if self.keys.get(getattr(self.key,self.controls.up),False):
                component.move_y(1)
            if self.keys.get(getattr(self.key,self.controls.down),False):
                component.move_y(-1)
            if self.keys.get(getattr(self.key,self.controls.right),False):
                component.move_x(1)
            if self.keys.get(getattr(self.key,self.controls.left),False):
                component.move_x(-1)
            if self.keys.get(getattr(self.key,self.controls.rotate_clockwise),False):
                component.rotate(1)
            if self.keys.get(getattr(self.key,self.controls.rotate_counter_clockwise),False):
                component.rotate(-1)

            # if self.keys.get(getattr(self.key,self.controls.toggle_rotate_clockwise),False):
            #     if self.toggle:
            #         self.toggle_clockwise = not self.toggle_clockwise
            #         self.toggle = False
            # if self.toggle_clockwise:
            #     component.rotate(1,dt)
            # if self.keys.get(getattr(self.key,self.controls.toggle_rotate_counter_clockwise),False):
            #     if self.toggle:
            #         self.toggle_counter_clockwise = not self.toggle_counter_clockwise
            #         self.toggle = False
            # if self.toggle_counter_clockwise:
            #     component.rotate(-1,dt)

            if self.toggle:
                if self.keys.get(getattr(self.key,self.controls.grow),False):
                    component.grow()
                    self.toggle = False
                if self.keys.get(getattr(self.key,self.controls.shrink),False):
                    component.shrink()
                    self.toggle = False
                if self.keys.get(getattr(self.key,self.controls.faster),False):
                    component.faster()
                    self.toggle = False
                if self.keys.get(getattr(self.key,self.controls.slower),False):
                    component.slower()
                    self.toggle = False
                if self.keys.get(getattr(self.key,self.controls.rotate_faster),False):
                    component.rotate_faster()
                    self.toggle = False
                if self.keys.get(getattr(self.key,self.controls.rotate_slower),False):
                    component.rotate_slower()
                    self.toggle = False
                try:
                    if self.keys.get(getattr(self.key,self.controls.fg_toggle),False):
                        if self.function_generator.status == 'ON':
                            self.function_generator.OFF()
                        else:
                            self.function_generator.ON()
                        self.toggle = False
                except Exception as e:
                    print(e)
                    pass
            
            try:
                if self.keys.get(getattr(self.key,self.controls.stage_up),False):
                    self.stage.move_relative(0,-self.stage_speed)
                if self.keys.get(getattr(self.key,self.controls.stage_down),False):
                    self.stage.move_relative(0,self.stage_speed)
                if self.keys.get(getattr(self.key,self.controls.stage_right),False):
                    self.stage.move_relative(self.stage_speed,0)
                if self.keys.get(getattr(self.key,self.controls.stage_left),False):
                    self.stage.move_relative(-self.stage_speed,0)
            except:
                pass
                
            if self.keys.get(getattr(self.key,self.controls.stage_faster),False):
                self.stage_speed+=1
            if self.keys.get(getattr(self.key,self.controls.stage_slower),False):
                if self.stage_speed>1:
                    self.stage_speed-=1                
            if self.keys.get(getattr(self.key,self.controls.toggle_display),False):
                if self.toggle:
                    component.toggle_display()
                    self.toggle = False
            if self.keys.get(getattr(self.key,self.controls.print_pose),False):
                print(component.pose)

