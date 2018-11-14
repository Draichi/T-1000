import keras, random
from keras.models import Sequential, load_model
from keras.layers import Dense, LSTM, Flatten, Dropout, BatchNormalization, GRU
# from tensorflow.keras.callbacks import TensorBoard, ModelCheckpoint
from keras.optimizers import Adam
import numpy as np
from collections import deque
from configs.vars import gamma, epsilon, epsilon_min, epsilon_decay, epochs

class Agent:
	def __init__(self, state_size, is_eval=False, model_name=""):
		self.state_size = state_size # normalized previous days
		self.action_size = 3 # sit, buy, sell
		self.memory = deque(maxlen=1000)
		self.inventory = []
		self.model_name = model_name
		self.is_eval = is_eval
		self.gamma = gamma
		self.epsilon = epsilon
		self.epsilon_min = epsilon_min
		self.epsilon_decay = epsilon_decay

		self.model = load_model("models/" + model_name) if is_eval else self._model()

	def _model(self):
		model = Sequential()

		# --------------LSTM------------- #
		# model.add(LSTM(128, input_shape=(self.state_size,3), activation='relu', return_sequences=True))
		# model.add(Dropout(0.2))
		# model.add(BatchNormalization())
		# model.add(LSTM(128, input_shape=(self.state_size,3), activation='relu', return_sequences=True))
		# model.add(Dropout(0.1))
		# model.add(BatchNormalization())
		# model.add(LSTM(128, input_shape=(self.state_size,3), activation='relu', return_sequences=True))
		# model.add(Dropout(0.2))
		# model.add(BatchNormalization())
		# model.add(Flatten())
		# model.add(Dense(32, activation="relu"))
		# model.add(Dropout(0.2))
		# --------------LSTM------------- #

		# --------------GRU-------------- #
		model.add(GRU(128, input_shape=(self.state_size,self.action_size), return_sequences=True))
		model.add(Dropout(0.2))
		model.add(BatchNormalization())
		model.add(GRU(64, input_shape=(self.state_size,self.action_size), return_sequences=True))
		model.add(Dropout(0.1))
		model.add(BatchNormalization())
		model.add(GRU(32, input_shape=(self.state_size,self.action_size), return_sequences=True))
		model.add(Dropout(0.2))
		model.add(BatchNormalization())
		model.add(Flatten())
		model.add(Dense(16, activation="relu"))
		model.add(Dropout(0.2))
		# --------------GRU-------------- #

		model.add(Dense(self.action_size, activation="linear"))

		# --------------OPTIMIZER-------------- #
		model.compile(loss="mse", optimizer="rmsprop")
		# model.compile(loss="mse", optimizer=Adam(lr=0.001))
		# --------------OPTIMIZER-------------- #

		return model

	def act(self, state):
		if not self.is_eval and random.random() <= self.epsilon:
			return random.randrange(self.action_size)

		options = self.model.predict(state)

		return np.argmax(options[0][0])

	def expReplay(self, batch_size):
		mini_batch = []
		l = len(self.memory)
		
		for i in range(l - batch_size + 1, l):
			mini_batch.append(self.memory.popleft())
		
		for state, action, reward, next_state, done in mini_batch:
			target = reward
			if not done:
				target = reward + self.gamma * np.amax(self.model.predict(next_state)[0])

			target_f = self.model.predict(state)
			
			target_f[0][action] = target
			self.model.fit(state, target_f, epochs=epochs, verbose=0)

		if self.epsilon > self.epsilon_min:
			self.epsilon *= self.epsilon_decay 

		# opt = tf.keras.optimizers.Adam(lr=0.001, decay=1e-6)
		# model.compile(optimizer=opt,loss='sparse_categorical_crossentropy',metrics=['accuracy'])
		# tensorboard = TensorBoard(log_dir=f'logs/{NAME}')
		# filepath = 'RNN-{epoch:02d}-{val_acc:.3f}'
		# checkpoint = ModelCheckpoint('models/{}.model'.format(filepath, monitor='val_acc',verbose=1,save_best_only=True,mode='max'))
		# history = model.fit(x_train,y_train,batch_size=BATCH_SIZE,epochs=EPOCHS,validation_data=(x_test,y_test),callbacks=[tensorboard,checkpoint])

