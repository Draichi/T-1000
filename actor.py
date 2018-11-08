# python 3.6

#virtualenv --system-site-packages -p python3.6
#source ./venv/bin/activate
#pip install -r requirements.txt
#deactivate

import tensorflow as tf 
import pandas as pd
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, LSTM, CuDNNLSTM, BatchNormalization, Flatten
from tensorflow.keras.callbacks import TensorBoard, ModelCheckpoint
from sklearn import preprocessing
import numpy as np
from collections import deque
import random, time

SEQ_LEN = 60
FUTURE_PERIOD_TO_PREDICT = 3
EPOCHS = 10
BATCH_SIZE = 64
# NAME = f'{SEQ_LEN}-SEQ-{FUTURE_PERIOD_TO_PREDICT}-PRED-{int(time.time())}'

CLOSE_COLUMN = 3

def classify(current, future):
    if float(future) > float(current):
        return 1
    else:
        return 0

def preprocess_df(df):
    df = df.drop('future',1)
    for col in df.columns:
        if col != 'target':
            df.replace([np.inf, -np.inf], np.nan, inplace=True)
            df[col] = df[col].pct_change() #normalizing 
            df.replace([np.inf, -np.inf], np.nan, inplace=True)
            df.fillna(0,inplace=True)
    sequential_data = []
    prev_days = deque(maxlen=SEQ_LEN)
    for i in df.values:
        prev_days.append([n for n in i[:-1]]) # every columns except target
        if len(prev_days) == SEQ_LEN:
            sequential_data.append([np.array(prev_days), i[-1]]) # feature and label
    random.shuffle(sequential_data)
    buys = []
    sells = []
    for seq, target in sequential_data:
        if target == 0:
            sells.append([seq, target])
        elif target == 1:
            buys.append([seq, target])
    lower = min(len(buys), len(sells)) # same amout of buys and sells for precision
    buys = buys[:lower]
    sells = sells[:lower]
    sequential_data = buys + sells
    random.shuffle(sequential_data)
    x = []
    y = []
    for seq, target in sequential_data:
        x.append(seq)
        y.append(target)
    return np.array(x), y

df = pd.read_csv('EURUSD_5.csv', skiprows=39, names=range(67)) # why skiprows (?)
df.replace([np.inf, -np.inf], np.nan)
df.dropna(inplace=True)

df['future'] = df[CLOSE_COLUMN].shift(-FUTURE_PERIOD_TO_PREDICT)
df['target'] = list(map(classify, df[CLOSE_COLUMN], df['future']))
times = sorted(df.index.values)
last_5pct = times[-int(0.05*len(times))]
validation_df = df[(df.index >= last_5pct)]
df = df[(df.index < last_5pct)]

x_train, y_train = preprocess_df(df)
# print(x_train.shape[1:])
# quit()
x_test, y_test = preprocess_df(validation_df)

print(type(x_train.shape))
print(x_train.shape)
print(type(x_train[0].shape))
print(x_train[0].shape)
print(type(x_train.shape[1:]))
print(x_train.shape[1:])
quit()

# print(f'train data: {len(x_train)}, validation: {len(x_test)}')
# print(f'dont buys: {y_train.count(0)}, buy: {y_train.count(1)} - must be pretty much the same')
# print(f'validation dont buys: {y_test.count(0)}, buy: {y_test.count(1)}')

model = Sequential()
model.add(LSTM(128, input_shape=(x_train.shape[1:]), activation='relu', return_sequences=True))
model.add(Dropout(0.2))
model.add(BatchNormalization())

model.add(LSTM(128, input_shape=(x_train.shape[1:]), activation='relu', return_sequences=True))
model.add(Dropout(0.1))
model.add(BatchNormalization())

model.add(LSTM(128, input_shape=(x_train.shape[1:]), activation='relu', return_sequences=True))
model.add(Dropout(0.2))
model.add(BatchNormalization())

model.add(Flatten())
model.add(Dense(32, activation='relu'))
model.add(Dropout(0.2))

model.add(Dense(2, activation='softmax'))

# opt = tf.keras.optimizers.Adam(lr=0.001, decay=1e-6)
# model.compile(optimizer=opt,loss='sparse_categorical_crossentropy',metrics=['accuracy'])
# tensorboard = TensorBoard(log_dir=f'logs/{NAME}')
# filepath = 'RNN-{epoch:02d}-{val_acc:.3f}'
# checkpoint = ModelCheckpoint('models/{}.model'.format(filepath, monitor='val_acc',verbose=1,save_best_only=True,mode='max'))
# history = model.fit(x_train,y_train,batch_size=BATCH_SIZE,epochs=EPOCHS,validation_data=(x_test,y_test),callbacks=[tensorboard,checkpoint])