def DNN(input_size, action_size):
    input_sample = keras.layers.Input(shape=input_size)  # TO DO: specify the input size

    x = keras.layers.Dense(512, input_shape=input_size, activation="relu", kernel_initializer='he_uniform')(
        input_sample)
    x = keras.layers.Dense(64, activation="relu", kernel_initializer='he_uniform')(x)

    x = keras.layers.Dense(action_size,  # TO DO: specify the number of neurons given the output_size
                           activation="linear",  # TO DO: specify a proper activation function for a regression problem
                           kernel_initializer='he_uniform')(x)

    model = keras.models.Model(inputs=input_sample, outputs=x)

    model.compile(loss="mse",  # TO DO: Choose a proper loss for regression
                  optimizer=keras.optimizers.RMSprop(learning_rate=0.00025, rho=0.95, epsilon=0.01),
                  metrics=["accuracy"])

    return model


class DQNAgent:
    def __init__(self):
        # Define the env
        self.env = gym.make('CartPole-v1')  # TO DO: Select the CartPole-v1

        self.state_size = 100
        self.action_size = self.env.action_space.n

        # Set hyperparameters
        self.runs = 1
        self.episodes = 1000  # by default, CartPole-v1 has max episode steps = 500
        self.memory = collections.deque(maxlen=2000)  # replay memory
        self.gamma = 0.95  # discount rate
        self.epsilon = 1.0  # exploration rate
        self.epsilon_min = 0.001
        self.epsilon_decay = 0.999
        self.batch_size = 64
        self.train_start = 1000
        self.R_final = []
        self.acc_reward = []

        # Create our main model
        self.model = DNN(input_size=(self.state_size,), action_size=self.action_size)
        self.model.summary()

    def greedy_exploration(self, state):
        p = np.random.random()  # TO DO: generate a random number between 0 and 1

        if p <= self.epsilon:  # exploration
            return random.randrange(self.action_size)
        else:  # explotaition
            return np.argmax(self.model.predict(state, verbose=0))  # action with maximum predicted Q value given state

    def fill_memory(self, state, action, reward, next_state, done):

        self.memory.append((state, action, reward, next_state, done))  # TO DO: append input arguments to the memory

        # once, it trains, explore more at the beginning
        if len(self.memory) > self.train_start:
            if self.epsilon > self.epsilon_min:
                self.epsilon *= self.epsilon_decay

    def train(self):
        # First fill memory with enough samples (1000) and then start training
        if len(self.memory) < self.train_start:
            return

        # construct training data from memory
        # randomly select samples from the memory to construct a batch
        memory_batch = random.sample(self.memory, min(len(self.memory), self.batch_size))

        state = np.zeros((self.batch_size, self.state_size))
        next_state = np.zeros((self.batch_size, self.state_size))

        action, reward, done = [], [], []

        for ind in range(self.batch_size):
            state[ind] = memory_batch[ind][0]
            action.append(memory_batch[ind][1])
            reward.append(memory_batch[ind][2])
            next_state[ind] = memory_batch[ind][3]
            done.append(memory_batch[ind][4])

        # Use our DNN to predict reward given a state
        # predicte next Qmax(s',a')
        target = self.model.predict(state)
        target_next = self.model.predict(next_state)

        # construct truth labels for training data
        for i in range(self.batch_size):
            if done[i]:
                target[i][action[i]] = reward[i]
            else:
                # Standard - DQN
                # DQN chooses the max Q value among next actions
                # selection and evaluation of action is on the target Q Network
                # Q_max = max_a' Q_target(s', a')

                target[i][action[i]] = reward[i] + self.gamma * (np.amax(target_next[i]))

        # Train our DNN with batches
        # Use verbose=1 see training accuracy
        self.model.fit(state, target, batch_size=self.batch_size, verbose=0)

    def run(self):
        for e in range(self.episodes):
            # Go to initial position
            state, _ = self.env.reset()
            done = False
            # get state
            state = np.reshape(state, [1, self.state_size])
            i = 0
            r_test = []
            r_test.append(0)

            while not done:
                # self.env.render()

                # select action randomly or following policy
                action = self.greedy_exploration(state)

                # perform  action
                next_state, reward, done, _, _ = self.env.step(action)
                next_state = np.reshape(next_state, [1, self.state_size])
                r_test.append(reward)

                if not done or i == self.env._max_episode_steps - 1:
                    reward = reward
                else:
                    reward = -100

                # Experience replay.
                # Save try in the memory D
                self.fill_memory(state, action, reward, next_state, done)

                # Update state
                state = next_state
                i = i + 1

                # If done, save trained model and exit
                if done:
                    self.acc_reward.append(i)
                    print("Episode:{}/{}, Accumulated Reward:{}, eps: {:.2}".format(e, self.episodes, i, self.epsilon))

                    # Save accumulated reward for plotting
                    if i == 500:
                        print("Saving trained model as cartpole-dqn.h5")
                        self.model.save("cartpole-dqn.h5")
                        return

                # Train model using replay memory
                self.train()

                # End of simulation step
            # Accumulated reward
            R = 0

            for t in range(len(r_test) - 1):
                R = R + (self.gamma ** (t)) * r_test[t + 1]

            self.R_final.append(R)

            # End of an episode
