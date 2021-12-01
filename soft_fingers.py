from dynamixel_driver import dxl
import numpy as np
import time
from multiprocessing import Process, Queue
import pygame


class SoftFingerModules():
    def __init__(self, motor_type="X",
                 device="/dev/ttyUSB1", baudrate=57600, protocol=2):

        self.finger1_id = [40, 41]
        self.finger2_id = [42, 43]
        self.finger3_id = [44, 45]
        self.object_id = [50]
        self.servos = dxl(motor_id=[
            *self.finger1_id, *self.finger2_id, *self.finger3_id, *self.object_id],
            motor_type=motor_type,
            devicename=device, baudrate=baudrate, protocol=protocol)
        self.servos.open_port()
        self.mid = np.pi
        range = 2.75
        self.min = {"left": self.mid - range/2, "right": self.mid + range/2}
        self.max = {"left": self.mid + range/4, "right": self.mid - range/4}
        self.finger_default = (self.min["left"], self.min["right"])
        self.theta_joints_nominal = np.array(self.finger_default * 3)

        self.func_names = {'move': self.finger_move,
                           'delta': self.finger_delta,
                           'idle': lambda: print('idle')}

        self.monitor_queue = Queue()
        # self.monitoring_process = Process(target=self.monitor_state, args=(self.monitor_queue,))
        # self.monitoring_process.start()
        time.sleep(1)
        self.reset()

    def reset(self):
        self.all_move(self.theta_joints_nominal)
        self.move_object(self.mid)
        self.servos.engage_motor(self.object_id, False)
        err_thresh = 0.05
        errs = np.array([np.inf] * 1)
        while np.any(errs > err_thresh):
            curr = self.get_pos()
            errs = np.abs(curr[-1] - np.pi)

    def monitor_state(self, queue):
        print("Begin monitoring.")
        pos = self.get_pos()[:-1]
        while True:
            while not queue.empty():
                signal = queue.get()
                if signal == 0:
                    break
            last_pos = pos
            try:
                pos = self.get_pos()[:-1]
                vel = pos - last_pos
                state = [pos, vel]
                # print(state)
                queue.put(state)
            except:
                continue


    def move_object(self, pos):
        self.servos.set_des_pos([self.servos.motor_id[-1]], [pos])

    def finger_delta(self, finger_num, dir):
        movements = {"up": np.array([0.1, -0.1]),
                     "down": np.array([-0.1, 0.1]),
                     "left": np.array([0.1, 0.1]),
                     "right": np.array([-0.1, -0.1])}
        assert dir in movements.keys()
        assert finger_num in [0, 1, 2]
        # curr = self.monitor_queue.get()[0]
        curr = self.get_pos()
        left = (finger_num)*2
        right = (finger_num)*2+1
        pos = np.array(curr[left:right+1])
        delta = movements[dir]
        new_pos = pos + delta
        return self.finger_move(finger_num, new_pos)

    def finger_move(self, finger_num, pos, err_thresh=0.1):
        assert finger_num in [0, 1, 2]
        left = (finger_num)*2
        right = (finger_num)*2+1
        self.servos.set_des_pos(self.servos.motor_id[left:right+1], pos)
        errs = np.array([np.inf, np.inf])
        while np.any(errs > err_thresh):
            # curr = self.monitor_queue.get()[0]
            curr = self.get_pos()
            errs = np.abs(curr[left:right+1] - pos)
        return curr

    def all_move(self, pos, err_thresh=0.1):
        for i in range(3):
            self.finger_move(i, pos[2*i:2*i+2])


    def get_pos(self):
        return self.servos.get_pos(self.servos.motor_id)

    def execute(self, command):
        func_name = command['func']
        assert func_name in self.func_names
        func = self.func_names[func_name]
        params = command['params']
        return func(*params)


def get_listener_funcs(queue, manipulator):
    def on_press(key):
        command = {'func': 'idle', 'params': None}
        try:
            if key == pygame.K_1:
                command = {'func': 'move', 'params': (
                    0, manipulator.finger_default)}
            elif key == pygame.K_2:
                command = {'func': 'move', 'params': (
                    1, manipulator.finger_default)}
            elif key == pygame.K_3:
                command = {'func': 'move', 'params': (
                    2, manipulator.finger_default)}
        except AttributeError:
            pass

        try:
            if key == pygame.K_w:
                command = {'func': 'delta', 'params': (0, 'up')}
            elif key == pygame.K_s:
                command = {'func': 'delta', 'params': (0, 'down')}
            elif key == pygame.K_a:
                command = {'func': 'delta', 'params': (0, 'left')}
            elif key == pygame.K_d:
                command = {'func': 'delta', 'params': (0, 'right')}
        except AttributeError:
            pass

        try:
            if key == pygame.K_i:
                command = {'func': 'delta', 'params': (1, 'up')}
            elif key == pygame.K_k:
                command = {'func': 'delta', 'params': (1, 'down')}
            elif key == pygame.K_j:
                command = {'func': 'delta', 'params': (1, 'left')}
            elif key == pygame.K_l:
                command = {'func': 'delta', 'params': (1, 'right')}
        except AttributeError:
            pass

        if key == pygame.K_UP:
            command = {'func': 'delta', 'params': (2, 'up')}
        elif key == pygame.K_DOWN:
            command = {'func': 'delta', 'params': (2, 'down')}
        elif key == pygame.K_LEFT:
            command = {'func': 'delta', 'params': (2, 'left')}
        elif key == pygame.K_RIGHT:
            command = {'func': 'delta', 'params': (2, 'right')}

        while not queue.empty():
            queue.get()
        queue.put(command)

        return True

    def on_release(key):
        try:
            if key == pygame.K_ESCAPE or key == pygame.K_q:
                return False
            else:
                return True
        except AttributeError:
            pass


    return on_press, on_release


def listen_keys(on_press, on_release):
    pygame.init()
    pygame.display.set_mode((640, 480))
    clock = pygame.time.Clock()
    run = True
    while run:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.KEYDOWN:
                run = on_press(event.key)
            elif event.type == pygame.KEYUP:
                run = on_release(event.key)



def collect_human_trajectory(manipulator):
    trajectory = []
    queue = Queue()
    on_press, on_release = get_listener_funcs(queue, manipulator)
    listener = Process(target=listen_keys, args=(on_press, on_release))
    listener.start()
    print("Starting keyboard listener.")
    while True:
        try:
            command = queue.get(False)
            print(f": {manipulator.execute(command)}")
        except:
            pass
        # print(f"\n {manipulator.get_pos()}")
        try:
            print(manipulator.monitor_queue.get(False))
        except:
            pass

        if not listener.is_alive():
            break

    print("Done")
    return listener, queue


if __name__ == "__main__":
    manipulator = SoftFingerModules()
    listener, queue = collect_human_trajectory(manipulator)
    manipulator.reset()
