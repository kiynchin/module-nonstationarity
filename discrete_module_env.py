from soft_fingers import SoftFingerModules
import gym
from gym import spaces
import numpy as np

class DiscreteModulesEnv(gym.Env):
    def __init__(self, goal_theta=0):
        self.goal_theta = goal_theta
        self.hardware = SoftFingerModules()
        self.action_space = spaces.Discrete(12)
        low = [-1.0]
        high = [1.0]
        self.observation_space = spaces.Box(
            low=np.array(low * 16),
            high=np.array(high *16),
            dtype=np.float64
        )
        self.action_map = []
        for finger in range(3):
            for dir in ("up", "down", "left", "right"):
                self.action_map.append((finger, dir))
        self.action_map = tuple(self.action_map)
        self.action_size = self.action_space.n
        self.observation_size = self.observation_space.shape[0]
        self.last_action = 0
        self.last_pos = self.theta_joints_nominal
        

    def _get_obs(self):
        all_theta = self.hardware.get_pos_all()
        theta_joints = all_theta[0:6]
        theta_t_obj = all_theta[6]
        theta_t_obj_sincos = [np.sin(theta_t_obj), np.cos(theta_t_obj)]
        theta_dot_joints = theta_joints - self.last_pos # TODO: Add instantaneous velocity
        last_action = self.last_action 
        dtheta_obj = theta_t_obj - self.goal_theta
        state = np.array([*theta_joints, 
                           *theta_dot_joints,
                           *theta_t_obj_sincos,
                           last_action,
                           dtheta_obj])
        # print(f"State: {state}")
        return state

    def step(self, action, thresh = 0.3/np.pi):
        self.last_action = self.env_action(action)
        self.last_pos = self.get_pos_fingers()
        idle_fingers = set(range(3))
        if action < self.action_size:
            finger, dir = self.action_map[action]
            idle_fingers.remove(finger)
            action = self.hardware.finger_delta(finger, dir, mag=0.6)
            for idle_finger in idle_fingers:
                action[idle_finger * 2: (idle_finger+1)*2] =  self.theta_joints_nominal[idle_finger *2 : (idle_finger+1)*2] 
        else:
            print("Invalid action")
            action = self.last_pos
        self.hardware.hardware_move(action)
        state = self._get_obs()
        reward = self.reward(state)
        err = np.abs(self.object_pos - self.goal_theta)
        done = err < thresh
        return state, reward, done, {}


    def decompose(self, state):
        theta_joints = state[0:6]
        theta_dot_joints = state[6:12]
        theta_t_obj_sincos = state[12:14]
        last_action = state[14]
        dtheta_obj = state[15]
        return theta_joints, theta_dot_joints, theta_t_obj_sincos, \
               last_action, dtheta_obj


    def one_if(self, x, thresh):
        # return 1 if x < thresh, 0 if not 
        if x < thresh:
            return 1
        else:
            return 0


    def reward(self, state):
        #rt=−5|∆θt,obj|−‖θnominal−θt‖−∥∥∥ ̇θt∥∥∥+ 10*1(|∆θt,obj|<0.25) + 50*1(|∆θt,obj|<0.1
        theta_joints, theta_dot_joints, _, _, dtheta_obj = self.decompose(state)
        return -5 * np.abs(dtheta_obj) \
                -0*np.linalg.norm(self.theta_joints_nominal - theta_joints) \
                -0*np.linalg.norm(theta_dot_joints) \
                + 10 * self.one_if(np.abs(dtheta_obj), thresh=0.45/np.pi) \
                + 50 * self.one_if(np.abs(dtheta_obj), thresh=0.30/np.pi)
    
    def interpret(self, command: int):
        if not command in range(self.action_size):
            action = None 
        action = command
        return action

    @property
    def object_pos(self):
        return self.hardware.get_pos_obj()[0]
        
    @property
    def theta_joints_nominal(self):
        return self.hardware.theta_joints_nominal

    def finger_move(self, finger_num, finger_pos):
        return self.hardware.finger_move(finger_num, finger_pos)

    def finger_delta(self, finger_num, dir):
        return self.hardware.finger_delta(finger_num, dir)

    def get_pos_fingers(self):
        return self.hardware.get_pos_fingers()

    def env_observation(self, obs):
        return self.hardware.env_observation(obs)
    
    def env_action(self, action):
        return action/self.action_size
        
    def reset(self):
        self.steps = 0
        self.hardware.reset()
        return self._get_obs()
    

gym.envs.register(
    id='DiscreteModulesEnv-v0',
    entry_point='discrete_module_env:DiscreteModulesEnv',
    kwargs={}
)

env_name = 'DiscreteModulesEnv-v0'

if __name__ == "__main__":
    env = DiscreteModulesEnv()
    import time
    for i in range(env.action_size):
        env.step(i)
        env.step(i)
        env.step(i)
        time.sleep(0.1)


