import os
import time
from collections import deque

import Parameters
import numpy as np
from Parameters import TREE_LEVELS, RANDOMNESS_MAX_VALUE
from tensorflow import keras


class rl_agent:
    # --- Hyperparameters ---
    def __init__(self, gamma=0.95, epsilon=1.0, epsilon_min=0.01, epsilon_decay=0.999, batch_size=1024, episodes=50):
        self.evaluation_mode = False
        self._gamma = gamma  # discount factor
        self._epsilon = epsilon  # exploration rate
        self._epsilon_min = epsilon_min
        self._epsilon_decay = epsilon_decay
        self._batch_size = batch_size
        self._episodes = episodes
        self.target_sync = 6000 // self._batch_size
        self.steps = 0
        self.rewards = 0
        # --- Replay buffer ---
        self.memory = deque(maxlen=4096)
        # --- Neural network ---
        self._state_dim = 56
        self._layer1_dim = 128
        self._hidden_dim = 64
        self._assoc = 4
        self.model = self.build_nn()
        self.target_model = self.build_nn()
        # --- load weights if available ---
        if os.path.exists("online_model.weights.h5"):
            print("Loading saved weights...")
            self.model.load_weights("online_model.weights.h5")
            self.target_model.load_weights("target_model.weights.h5")
        else:
            print("No saved weights found, starting fresh.")
        # --- Reward Tracker ---
        self.pending_events = []
        self.timeout = 100_000

    def build_nn(self):
        # --- Q-Network ---
        model = keras.Sequential([
            keras.layers.Dense(self._layer1_dim, activation="relu", input_shape=(self._state_dim,)),
            keras.layers.Dense(self._hidden_dim, activation="relu"),
            keras.layers.Dense(self._assoc, activation="linear")
        ])
        model.compile(optimizer=keras.optimizers.Adam(learning_rate=0.001),
                      loss='mse')
        return model

    def update_target_model(self):
        self.target_model.set_weights(self.model.get_weights())

    def choose_action(self, state):
        if np.random.rand() < self._epsilon and self.evaluation_mode == False:
            return np.random.choice(self._assoc)
        state_vec = np.array(state, dtype=np.float32).reshape(1, -1)
        q_values = self.model(state_vec, training=False).numpy()

        return np.argmax(q_values[0])

    def store_transition(self, state, action, reward, next_state, done=False):
        if self.evaluation_mode:
            return
        if Parameters.instructions_number > 1000000:
            start = time.time()
            # code you want to time

            self.memory.append((state, action, reward, next_state, done))
            end = time.time()
            print("Store transistion excluding replay:", end - start, "seconds")
            self.replay()
            self.rewards += reward
        if done:

            # Save online model weights
            self.model.save_weights("online_model.weights.h5")
            # Save target model weights
            self.target_model.save_weights("target_model.weights.h5")
            self.reset()

    def replay(self):
        if self.evaluation_mode:
            return
        if len(self.memory) < self._batch_size or Parameters.instructions_number < 1000_000:
            return
        self.steps += 1

        minibatch = [self.memory.popleft() for _ in range(self._batch_size)]
        states = np.array([s for s, _, _, _, _ in minibatch])
        actions = np.array([a for _, a, _, _, _ in minibatch])
        rewards = np.array([r for _, _, r, _, _ in minibatch])
        next_states = np.array([ns for _, _, _, ns, _ in minibatch])
        dones = np.array([d for _, _, _, _, d in minibatch])

        # code you want to time
        target_q = self.model.predict(states, verbose=0)
        next_q = self.target_model.predict(next_states, verbose=0)
        start_replay = time.time()
        for i in range(self._batch_size):
            target = rewards[i]
            if not dones[i]:
                target += self._gamma * np.max(next_q[i])
            target_q[i][actions[i]] = target

        self.model.fit(states, target_q, epochs=1, verbose=0)
        if self.steps % self.target_sync == 0:
            self.update_target_model()

        if self._epsilon > self._epsilon_min:
            self._epsilon *= self._epsilon_decay
        end_replay = time.time()
        print("Replay took:", end_replay - start_replay, "seconds")
    # --- Reward Tracking ---
    def add_event(self, evicted, inserted, state, action, next_state, way0, way1, way2):
        if self.evaluation_mode:
            return
        event = {
            "evicted": evicted,
            "inserted": inserted,
            "state": state,
            "action": action,
            "next_state": next_state,
            "age": Parameters.instructions_number,
            "way0": way0,
            "way1": way1,
            "way2": way2,
            "reward": 3
        }
        self.pending_events.append(event)

    def resolve(self, access_addr):
        if self.evaluation_mode:
            return
        start = time.time()
        for event in self.pending_events:
            if access_addr == event["way0"]:
                event["way0"] = None
            elif access_addr == event["way1"]:
                event["way1"] = None
            elif access_addr == event["way2"]:
                event["way2"] = None
            elif access_addr == event["inserted"]:
                event["reward"] += 0.01
                event["inserted"] = None

            if access_addr == event["evicted"]:
                self.store_transition(event["state"], event["action"], -3, event["next_state"])
                self.pending_events.remove(event)
            elif event["way0"] == None and event["way1"] == None and event["way2"] == None and event[
                "inserted"] == None:
                self.store_transition(event["state"], event["action"], event["reward"], event["next_state"])
                self.pending_events.remove(event)
            if Parameters.instructions_number - event["age"] > self.timeout:
                try:
                    self.pending_events.remove(event)
                except:
                    pass
        end = time.time()
        print("resolve() took", end - start, "seconds")

    def reset(self):
        self.pending_events.clear()
        self.steps = 0
        self.rewards = 0

def normalize(x, max_val):
    if max_val == 0: return 0.0
    return min(1.0, x / max_val)


def one_hot(val, categories):
    vec = [0] * len(categories)
    if val in categories:
        vec[categories.index(val)] = 1
    return vec


def build_state(ways_hits, request_address, pc, access_type, access_level, ways_levels, ways_preuse, ways_dirty,
                ways_lazy_updated):
    features = []
    block_offset = (request_address) & 0x3F
    set_index = (request_address >> 6) & 0x3FF
    categories = list(range(TREE_LEVELS))

    for i in range(len(ways_hits)):
        features.append(normalize(ways_hits[i], 1000))  # 0,1,2,3
    features.append(normalize(block_offset, 64))  # 4
    features.append(normalize(set_index, 1024))  # 5
    features.append(normalize(pc & 0xFFFF, 0xFFFF))  # 6
    features.append(access_type)  # 7
    features += (one_hot(access_level, categories))  # 8,9,10,11,12,13,14
    for i in range(len(ways_levels)):
        features += (one_hot(ways_levels[i], categories))  # 16,17,18,19,20,21,22, -
    for i in range(len(ways_preuse)):
        features.append(normalize(ways_preuse[i], 3000))
    features += (ways_dirty)
    features += (ways_lazy_updated)
    features.append(normalize(Parameters.randomness, RANDOMNESS_MAX_VALUE))

    return features


rl = rl_agent()
