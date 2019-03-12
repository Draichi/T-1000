import keras, random
from keras.models import Sequential, load_model
from keras.layers import Dense, LSTM, Flatten, Dropout, BatchNormalization, GRU, Conv1D, MaxPooling1D, PReLU, Bidirectional
# from tensorflow.keras.callbacks import TensorBoard, ModelCheckpoint
from keras.optimizers import Adam
import numpy as np
from collections import deque
from configs.vars import gamma, epsilon, epsilon_min, epsilon_decay, epochs, n_features

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
		model.add(LSTM(128, input_shape=(1,1), activation='relu', return_sequences=True))
		model.add(Dropout(0.2))
		model.add(BatchNormalization())
		model.add(LSTM(128, input_shape=(self.state_size,1), activation='relu', return_sequences=True))
		model.add(Dropout(0.1))
		model.add(BatchNormalization())
		model.add(LSTM(128, input_shape=(self.state_size,1), activation='relu', return_sequences=True))
		model.add(Dropout(0.2))
		model.add(BatchNormalization())
		model.add(Flatten())
		model.add(Dense(32, activation="relu"))
		model.add(Dropout(0.2))
		# --------------LSTM------------- #

		# --------------GRU-------------- #
		# model.add(GRU(128, input_shape=(self.state_size,n_features), return_sequences=True))
		# model.add(Dropout(0.2))
		# model.add(BatchNormalization())
		# model.add(GRU(64, input_shape=(self.state_size,n_features), return_sequences=True))
		# model.add(Dropout(0.1))
		# model.add(BatchNormalization())
		# model.add(GRU(64, input_shape=(self.state_size,n_features), return_sequences=True))
		# model.add(Dropout(0.2))
		# model.add(BatchNormalization())
		# model.add(Flatten())
		# model.add(Dense(32, activation="relu"))
		# model.add(Dropout(0.2))
		# --------------GRU-------------- #

        # ----------------CONV2D-----------------#
		# model.add(Dense(512,input_shape=(self.state_size,n_features)))
		# model.add(Conv1D(filters=32,kernel_size=1, dilation_rate=2, activation='relu',padding='valid', kernel_initializer='he_normal', kernel_regularizer=keras.regularizers.l2(0.005), input_shape=(self.state_size,n_features)))
		# model.add(Dropout(0.1))
		# model.add(Conv1D(kernel_size = (1), filters = 32, dilation_rate=4, padding='valid', kernel_initializer='he_normal', activation='relu',kernel_regularizer=keras.regularizers.l2(0.005)))
		# model.add(Dropout(0.2))
		# model.add(Conv1D(kernel_size = (1), filters = 64, dilation_rate=8, padding='valid', kernel_initializer='he_normal', activation='relu',kernel_regularizer=keras.regularizers.l2(0.005)))
		# model.add(Dropout(0.1))
		# model.add(Conv1D(kernel_size = (1), filters = 64, dilation_rate=16, padding='valid', kernel_initializer='he_normal', activation='relu',kernel_regularizer=keras.regularizers.l2(0.005)))
		# model.add(MaxPooling1D())
		# model.add(Dropout(0.2))
		# model.add(Conv1D(kernel_size = (1), filters = 64, dilation_rate=32, padding='valid', kernel_initializer='he_normal', activation='relu',kernel_regularizer=keras.regularizers.l2(0.005)))
		# model.add(Dropout(0.1))
		# model.add(Conv1D(kernel_size = (1), filters = 128, strides=2, padding='valid', kernel_initializer='he_normal', activation='relu',kernel_regularizer=keras.regularizers.l2(0.005)))
		# model.add(Dropout(0.2))
		# model.add(Conv1D(kernel_size = (1), filters = 128, strides=2, padding='valid', kernel_initializer='he_normal', activation='relu',kernel_regularizer=keras.regularizers.l2(0.005)))
		# model.add(Dropout(0.1))
		# model.add(Conv1D(kernel_size = (1), filters = 128, strides=2, padding='valid', kernel_initializer='he_normal', activation='relu',kernel_regularizer=keras.regularizers.l2(0.005)))
		# model.add(Dropout(0.2))
		# model.add(Bidirectional(GRU(48,return_sequences=True),merge_mode='concat'))
		# model.add(PReLU())
		# model.add(Flatten())
		# model.add(Dense(24, use_bias=False))
		# #model.add(LeakyReLU(alpha=0.1))
		# model.add(PReLU())
		# model.add(Dense(12, use_bias=False))
		# #model.add(LeakyReLU(alpha=0.1))
		# model.add(PReLU())
		#adamw =  AdamW(lr=self.learning_rate, beta_1=0.9, beta_2=0.999, epsilon=1e-08, decay=0.0, weight_decay=0.025, batch_size=1, samples_per_epoch=1, epochs=1)
		# adam = keras.optimizers.Adam(lr=0.0001, beta_1=0.9, beta_2=0.999, epsilon=1e-08, decay=0.0)
		# ---------------CONV2D--------------

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
			# if not done:
			# 	target = reward + self.gamma * np.amax(self.model.predict(next_state)[0])
			target_f = self.model.predict(state)
			
			target_f[0][action] = target
			self.model.fit(state, target_f, epochs=epochs, verbose=0)
		
		if self.epsilon > self.epsilon_min:
			self.epsilon *= self.epsilon_decay 
