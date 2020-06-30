# %tensorflow_version 2.x
# %matplotlib inline
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
from numpy import concatenate
from pandas import read_csv
from pandas import DataFrame
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.layers import LSTM
from matplotlib.pyplot import figure
import matplotlib.dates as mdates
import tensorflow as tf

n_timesteps = 96
n_features = 14
n_samples = 691

workspace = input("Set Workspace: ")

# load data
choose_forecast = int(input("start_time[1] or ramping[2]?: ")) # choose wether to train ramping or start time model

# input model hyperparameters
n_layers = int(input("Number of LSTM layers: "))
n_neurons = int(input("Number of neurons per layer: "))
batch_size = int(input("Batchsize: "))
epochs = int(input("Number of Epochs to train the model: "))
dropout = float(input("Dropout value (0.0 - 1.0): "))
learning_rate = float(input("Learning rate of optimizer: "))

if choose_forecast == 2:
  features = np.loadtxt("ramping_data.txt")
  features = features.reshape((n_samples,n_timesteps*n_features))
  target = np.loadtxt("ramping_target.txt")
elif choose_forecast == 1:
  features = np.loadtxt("start_time_data.txt")
  features = features.reshape((n_samples,n_timesteps*n_features))
  target = np.loadtxt("start_time_target.txt")
else:
  "Wrong value!"

time = pd.read_csv(workspace + "time.csv",sep=";",index_col=0)


# scaling
scaled_features = features.reshape((n_samples,n_timesteps*n_features))
X_standard_scaler = StandardScaler()
X_minmax_scaler = MinMaxScaler(feature_range=(-1, 1))
scaled_features = X_standard_scaler.fit_transform(scaled_features)
scaled_features = X_minmax_scaler.fit_transform(scaled_features)
scaled_features = scaled_features.reshape((n_samples, n_timesteps, n_features))

# concatenation of scaled features and one-hot-encoded features
X = np.empty((n_samples,n_timesteps,n_features+19))
for r in range(0,n_samples):
  for t in range(n_timesteps):
    X[r,t] = np.concatenate((scaled_features[r,t],time.iloc[r].values))

Y_standard_scaler = StandardScaler()	
Y_minmax_scaler = MinMaxScaler(feature_range=(-1, 1))
Y = Y_standard_scaler.fit_transform(target.reshape(-1,1))
Y = Y_minmax_scaler.fit_transform(Y)

# split into training, test and validation set
split_1 = 570
split_2 = 631

train_X = X[:split_1]
val_X = X[split_1:split_2]
test_X = X[split_2:]
train_y = Y[:split_1]
val_y = Y[split_1:split_2]
test_y = Y[split_2:]


time = time.iloc[:n_samples+1]
start_date = time.index[0] 
split_1_date = time.index[split_1]
split_2_date = time.index[split_2]
end_date = time.index[-1]
start_y, start_m, start_d = int(start_date[-4:]), int(start_date[3:5]), int(start_date[:2])
split_1_y, split_1_m, split_1_d = int(split_1_date[-4:]), int(split_1_date[3:5]), int(split_1_date[:2])
split_2_y, split_2_m, split_2_d = int(split_2_date[-4:]), int(split_2_date[3:5]), int(split_2_date[:2])
end_y, end_m, end_d = int(end_date[-4:]), int(end_date[3:5]), int(end_date[:2]) 

# build model
def lstm(n_layers,n_neurons,dropout):
  model = Sequential()
  
  if n_layers == 1:
    model.add(LSTM(n_neurons, input_shape=(train_X.shape[1], train_X.shape[2]), dropout = dropout))
  else:
    model.add(LSTM(n_neurons, input_shape=(train_X.shape[1], train_X.shape[2]), return_sequences=True))
    for i in range(n_layers-2):
      model.add(LSTM(n_neurons, activation='tanh',return_sequences = True))
    model.add(LSTM(n_neurons, activation='tanh', dropout = dropout))
  model.add(Dense(1))
  # opt = tf.keras.optimizers.Adam(learning_rate=0.001,clipnorm = 1.0)
  opt = tf.keras.optimizers.Adam(learning_rate = learning_rate)
  model.compile(loss='mse', optimizer="adam",  metrics=['mae','mape'])
  return model

def makePredictions(model, testX,testY):
  yhat = model.predict(testX)
  
  inv_yhat = Y_standard_scaler.inverse_transform(yhat.reshape(-1,1))
  inv_yhat = Y_minmax_scaler.inverse_transform(inv_yhat)
  inv_yhat = inv_yhat[:,0]

  inv_y = Y_standard_scaler.inverse_transform(testY.reshape(-1,1))
  inv_y = Y_minmax_scaler.inverse_transform(inv_y)
  inv_y = inv_y[:,0]
  return inv_y, inv_yhat

def plotResults(predictions, real_values):
  customTag = 'test_plot'
  figure(num=None, figsize=(16, 12), dpi=80, facecolor='w', edgecolor='k')
  plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d/%Y'))
  plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval = 7)) 
  start = datetime.date(split_2_y,split_2_m,split_2_d)
  end = datetime.date(end_y,end_m,end_d)
  days = mdates.drange(start,end,datetime.timedelta(days=1)) 
  inv_y = real_values
  inv_yhat = predictions
  plt.plot(days,inv_y[:-1])
  plt.plot(days, inv_yhat[:-1])
  plt.legend(('true','prediction'))
  plt.title('Test Predictions', fontsize=20)
  plt.xticks(rotation= 45)
  plt.savefig(workspace + '/' + customTag + '.png', bbox_inches="tight")

# checkpoint model with lowest validation loss
model_checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
    filepath=workspace+'/',
    save_weights_only=False,
    monitor='val_loss',
    mode='min',
    save_freq='epoch',
    save_best_only=True)

model = lstm(n_layers,n_neurons,dropout)
model.fit(train_X, train_y, epochs=epochs, batch_size=batch_size, validation_data=(val_X, val_y), verbose=1, shuffle=False, callbacks=[model_checkpoint_callback])

# Make predictions on test set and plot them
inv_y, inv_yhat = makePredictions(model,val_X,val_y)
plotResults(inv_yhat,inv_y)