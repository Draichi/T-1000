import keras, random
from keras.models import Sequential, load_model
from keras.layers import Dense, LSTM
from keras.optimizers import Adam
import numpy as np
from collections import deque

class Agent:
	def __init__(self, state_size, is_eval=False, model_name=""):
		self.state_size = state_size # normalized previous days
		self.action_size = 3 # sit, buy, sell
		self.memory = deque(maxlen=1000)
		self.inventory = []
		self.model_name = model_name
		self.is_eval = is_eval

		self.gamma = 0.95
		self.epsilon = 1.0
		self.epsilon_min = 0.01
		self.epsilon_decay = 0.995

		self.model = load_model("models/" + model_name) if is_eval else self._model()

	def _model(self):
		# print(type(self.state_size))
		# print(self.state_size)
		# quit()
		model = Sequential()
		model.add(LSTM(128, input_shape=(10,2), activation='relu', return_sequences=True))

		# model.add(Dense(units=128, input_dim=(10,), activation="relu"))
		model.add(Dense(units=64, activation="relu"))
		model.add(Dense(units=32, activation="relu"))
		model.add(Dense(units=8, activation="relu"))
		model.add(Dense(self.action_size, activation="linear"))
		model.compile(loss="mse", optimizer=Adam(lr=0.001))

		return model

	def act(self, state):
		if not self.is_eval and random.random() <= self.epsilon:
			return random.randrange(self.action_size)

		options = self.model.predict(state)
		# print('==options==',options)
		print('==options[0]==')
		print('==options[0]==',state)
		print('==options[0]==',options)
		print('==options[0]==',options[0])
		print('==options[0]==',np.argmax(options[0]))
		quit()

		return np.argmax(options[0])

	def expReplay(self, batch_size):
		mini_batch = []
		l = len(self.memory)
		# print('self.memory',self.memory)
		# quit()
		
		for i in range(l - batch_size + 1, l):
			mini_batch.append(self.memory.popleft())
		# print(mini_batch)
		# quit()
		for state, action, reward, next_state, done in mini_batch:
			target = reward
			if not done:
				target = reward + self.gamma * np.amax(self.model.predict(next_state)[0])

			target_f = self.model.predict(state)

			# print('==target_f==',target_f)
			# print('==action==',action)
			# print('==target==',target)
			# print('==target_f[0][0]==',target_f[0][0])
			# print('==target=',target)
			# print('==action=',action)
			# print('==state=',state)
			target_f[0][action] = target
			self.model.fit(state, target_f, epochs=1, verbose=0)

		if self.epsilon > self.epsilon_min:
			self.epsilon *= self.epsilon_decay 
