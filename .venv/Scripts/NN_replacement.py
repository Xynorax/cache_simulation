import pickle
import random
from collections import deque

import Parameters
import numpy as np
from Parameters import DATA_MEM_SIZE, TREE_LEVELS, RANDOMNESS_MAX_VALUE
from tensorflow import keras
from tensorflow.keras import layers


# ------------------ Replay Buffer ------------------
class ReplayBuffer:
    def __init__(self, capacity=70000):
        self.buf = deque(maxlen=capacity)
        self.path = "replay_buffer.pkl"

    def push(self, s, a, r, ns, done):
        self.buf.append((s, a, r, ns, done))

    def load(self):
        with open(self.path, "rb") as f:
            self.buf = pickle.load(f)

    def sample(self, n):
        batch = random.sample(self.buf, n)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (np.array(states, dtype=np.float32),
                np.array(actions, dtype=np.int32),
                np.array(rewards, dtype=np.float32),
                np.array(next_states, dtype=np.float32),
                np.array(dones, dtype=bool))

    def save(self):
        with open(self.path, "wb") as f:
            pickle.dump(self.buf, f)

    def __len__(self): return len(self.buf)


def build_victim_net(state_dim, hidden_dim, assoc):
    model = keras.Sequential([
        layers.Input(shape=(state_dim,)),
        layers.Dense(hidden_dim, activation="relu"),
        layers.Dense(hidden_dim // 4, activation="relu"),
        layers.Dense(assoc, activation=None)  # linear outputs
    ])
    model.compile(optimizer=keras.optimizers.Adam(1e-3),
                  loss=keras.losses.Huber())  # smooth L1 like DQN
    return model


# ------------------ Policy Wrapper ------------------
class NNReplacementPolicy:
    def __init__(self, assoc=8, state_dim=100, hidden_dim=256,
                 epsilon=1.0, gamma=0.98, batch_size=256,
                 target_sync=500, evaluate_mode=False):
        self.assoc = assoc
        self.epsilon = epsilon
        self.gamma = gamma
        self.batch_size = batch_size
        self.target_sync = target_sync
        self.epsilon_decay = 0.99

        self.net = build_victim_net(state_dim, hidden_dim, assoc)
        self.target = build_victim_net(state_dim, hidden_dim, assoc)
        self.target.set_weights(self.net.get_weights())
        self.checkpoint_path = "policy.weights.h5"
        self.reward_file_path = "rewards.txt"
        self.total_reward = 0
        self.episode = 0
        self.evaluate_mode = evaluate_mode

        try:
            # self.net.load_weights(self.checkpoint_path)
            # self.target.load_weights(self.checkpoint_path)
            print(f"[INFO] Loaded weights from {self.checkpoint_path}")
        except Exception:
            print("[INFO] No saved weights found, starting fresh.")
        self.replay = ReplayBuffer()
        self.steps = 0

    # -------- Action selection on a miss --------
    def choose_victim(self, state_vec):
        state_vec = np.array(state_vec, dtype=np.float32).reshape(1, -1)
        if not self.evaluate_mode and random.random() < self.epsilon:
            return random.randrange(self.assoc)
        q_values = self.net.predict(state_vec, verbose=0)[0]
        return int(np.argmax(q_values))

    # -------- Store transition --------
    def store(self, state, action, reward, next_state, done=False):
        if self.evaluate_mode:
            # Only accumulate total reward, don't store in replay
            self.total_reward += reward
            if done:
                self.episode += 1
                with open(self.reward_file_path, "a") as f:
                    f.write(f"Episode {self.episode}: Total Reward = {self.total_reward}  Epsilon = {self.epsilon}\n")
                self.total_reward = 0
            return
        self.total_reward += reward
        self.replay.push(state, action, reward, next_state, done)
        self.steps += 1
        if len(self.replay) >= self.batch_size and self.steps > 1000:
            self.train_step()
        # if self.steps % self.target_sync == 0:
        #    self.target.set_weights(self.net.get_weights())
        # Polyak averaging
        net_weights = self.net.get_weights()
        target_weights = self.target.get_weights()
        new_weights = []
        for nw, tw in zip(net_weights, target_weights):
            new_weights.append(0.002 * nw + (1 - 0.002) * tw)
        self.target.set_weights(new_weights)
        if done == True:
            self.episode += 1
            with open(self.reward_file_path, "a") as f:
                f.write(f"Episode {self.episode}: Total Reward = {self.total_reward}  Epsilon = {self.epsilon}\n")
            self.total_reward = 0

    # -------- Training update --------
    def train_step(self):
        # Sample batch
        states, actions, rewards, next_states, dones = self.replay.sample(self.batch_size)

        # Predict current Q-values (online net)
        q_values = self.net.predict(states, verbose=0)

        # Make a copy to modify as targets
        q_values_target = q_values.copy()

        # Predict next Q-values (online net for argmax selection)
        q_next_online = self.net.predict(next_states, verbose=0)

        # Predict next Q-values (target net for stable evaluation)
        q_next_target = self.target.predict(next_states, verbose=0)

        # Select best actions from online net
        next_actions = np.argmax(q_next_online, axis=1)

        # Update Q-values using Double DQN rule
        for i in range(self.batch_size):
            a = actions[i]
            if dones[i]:
                q_values_target[i, a] = rewards[i]
            else:
                q_values_target[i, a] = rewards[i] + \
                                        self.gamma * q_next_target[i, next_actions[i]]

        # Train on updated targets
        self.net.fit(states, q_values_target, epochs=1, verbose=0)

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


nn_policy = NNReplacementPolicy(evaluate_mode=True)
