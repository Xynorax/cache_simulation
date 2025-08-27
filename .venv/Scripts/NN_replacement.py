import random
from collections import deque

import Parameters
import numpy as np
from Parameters import DATA_MEM_SIZE, TREE_LEVELS, RANDOMNESS_MAX_VALUE
from tensorflow import keras
from tensorflow.keras import layers


# ------------------ Replay Buffer ------------------
class ReplayBuffer:
    def __init__(self, capacity=200_000):
        self.buf = deque(maxlen=capacity)

    def push(self, s, a, r, ns, done):
        self.buf.append((s, a, r, ns, done))

    def sample(self, n):
        batch = random.sample(self.buf, n)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (np.array(states, dtype=np.float32),
                np.array(actions, dtype=np.int32),
                np.array(rewards, dtype=np.float32),
                np.array(next_states, dtype=np.float32),
                np.array(dones, dtype=bool))

    def __len__(self): return len(self.buf)


def build_victim_net(state_dim, hidden_dim, assoc):
    model = keras.Sequential([
        layers.Input(shape=(state_dim,)),
        layers.Dense(hidden_dim, activation="relu"),
        layers.Dense(assoc, activation=None)  # linear outputs
    ])
    model.compile(optimizer=keras.optimizers.Adam(1e-3),
                  loss=keras.losses.Huber())  # smooth L1 like DQN
    return model


# ------------------ Policy Wrapper ------------------
class NNReplacementPolicy:
    def __init__(self, assoc=8, state_dim=100, hidden_dim=128,
                 epsilon=0.1, gamma=0.99, batch_size=256,
                 target_sync=10_000):
        self.assoc = assoc
        self.epsilon = epsilon
        self.gamma = gamma
        self.batch_size = batch_size
        self.target_sync = target_sync

        self.net = build_victim_net(state_dim, hidden_dim, assoc)
        self.target = build_victim_net(state_dim, hidden_dim, assoc)
        self.target.set_weights(self.net.get_weights())
        self.checkpoint_path = "policy.weights.h5"

        try:
            self.net.load_weights(self.checkpoint_path)
            self.target.load_weights(self.checkpoint_path)
            print(f"[INFO] Loaded weights from {self.checkpoint_path}")
        except Exception:
            print("[INFO] No saved weights found, starting fresh.")
        self.replay = ReplayBuffer()
        self.steps = 0

    # -------- Action selection on a miss --------
    def choose_victim(self, state_vec):
        state_vec = np.array(state_vec, dtype=np.float32).reshape(1, -1)
        if random.random() < self.epsilon:
            return random.randrange(self.assoc)
        q_values = self.net.predict(state_vec, verbose=0)[0]
        return int(np.argmax(q_values))

    # -------- Store transition --------
    def store(self, state, action, reward, next_state, done=False):
        self.replay.push(state, action, reward, next_state, done)
        self.steps += 1
        if len(self.replay) >= self.batch_size:
            self.train_step()
        if self.steps % self.target_sync == 0:
            self.target.set_weights(self.net.get_weights())

    # -------- Training update --------
    def train_step(self):
        states, actions, rewards, next_states, dones = self.replay.sample(self.batch_size)

        # Current Q-values
        q_values = self.net.predict(states, verbose=0)

        # Target Q-values from target network
        q_next = self.target.predict(next_states, verbose=0)

        # Update Q for taken actions
        for i in range(self.batch_size):
            a = actions[i]
            if dones[i]:
                q_values[i, a] = rewards[i]
            else:
                q_values[i, a] = rewards[i] + self.gamma * np.max(q_next[i])

        # Train on updated targets
        self.net.fit(states, q_values, epochs=1, verbose=0)

    def save(self):
        self.net.save_weights(self.checkpoint_path)
        print(f"[INFO] Weights saved to {self.checkpoint_path}")


def to_binary(x, bits):
    return [(x >> i) & 1 for i in range(bits)]


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
    set_index = (request_address >> 6) & 0x7FF
    categories = list(range(TREE_LEVELS))

    for i in range(len(ways_hits)):
        features.append(normalize(ways_hits[i], 100000))  # 0,1,2,3
    features.append(normalize(block_offset, 64))  # 4
    features.append(normalize(set_index, 1024))  # 5
    features.append(normalize(pc, DATA_MEM_SIZE))  # 6
    features.append(access_type)  # 7
    features += (one_hot(access_level, categories))  # 8,9,10,11,12,13,14
    for i in range(len(ways_levels)):
        features += (one_hot(ways_levels[i], categories))  # 16,17,18,19,20,21,22, -
    for i in range(len(ways_preuse)):
        features.append(normalize(ways_preuse[i], 100000))
    features += (ways_dirty)
    features += (ways_lazy_updated)
    features.append(normalize(Parameters.randomness, RANDOMNESS_MAX_VALUE))

    return features
