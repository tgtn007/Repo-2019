import matplotlib as mpl
from matplotlib import pylab as plt
import matplotlib.dates as mdates
import seaborn as sns
import numpy as np
import tensorflow as tf
import tensorflow_probability as tfp
from tensorflow_probability import distributions as tfd
from tensorflow_probability import sts
import pandas as pd  
from sklearn.preprocessing import MinMaxScaler
import tensorflow_probability as tfp

dataframe = pd.read_csv('international-airline-passengers.csv', usecols=[1], engine='python', skipfooter=3)
dataset = dataframe.values
dataset = np.array(dataset.astype('float32'))


X0=dataset[0:-12]
Y0=dataset[-12:]


def build_model(observed_time_series):
  trend = sts.LocalLinearTrend(observed_time_series=observed_time_series)
  seasonal = tfp.sts.Seasonal(
      num_seasons=12, observed_time_series=observed_time_series)
  model = sts.Sum([trend, seasonal], observed_time_series=observed_time_series)
  return model

tf.reset_default_graph()
series_model = build_model(X0)

# Build the variational loss function and surrogate posteriors `qs`.
with tf.variable_scope('sts_elbo', reuse=tf.AUTO_REUSE):
  elbo_loss, variational_posteriors = tfp.sts.build_factored_variational_loss(
      series_model,
      observed_time_series=X0)
  
num_variational_steps = 300 # @param { isTemplate: true}
num_variational_steps = int(num_variational_steps)

train_vi = tf.train.AdamOptimizer(0.1).minimize(elbo_loss)

with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())
    for i in range(num_variational_steps):
        _, elbo_ = sess.run((train_vi, elbo_loss))
        if i % 20 == 0:
            print("step {} -ELBO {}".format(i, elbo_))
    # Draw samples from the variational posterior.
    samples = sess.run({k: q.sample(50) for k, q in variational_posteriors.items()})

print("Inferred parameters:")
for param in series_model.parameters:
    print("{}: {} +- {}".format(param.name,
                              np.mean(samples[param.name], axis=0),
                              np.std(samples[param.name], axis=0)))
num_forecast_steps=12
series_forecast_dist = tfp.sts.forecast(
    series_model,
    observed_time_series=X0,
    parameter_samples=samples,
    num_steps_forecast=num_forecast_steps)

series_forecast_dist

num_samples=10

with tf.Session() as sess:
  series_forecast_mean, series_forecast_scale, series_forecast_samples = sess.run(
      (series_forecast_dist.mean()[..., 0],
       series_forecast_dist.stddev()[..., 0],
       series_forecast_dist.sample(num_samples)[..., 0]))

x=np.linspace(0,len(X0),len(X0))
num_steps = len(X0)
num_steps_forecast = series_forecast_mean.shape[-1]
num_steps_train = num_steps - num_steps_forecast
forecast_steps = np.arange(
      x[num_steps_train],
      x[num_steps_train]+num_steps_forecast,
      dtype=x.dtype)

plt.figure(figsize=(10,7))
plt.plot(forecast_steps,Y0,color='red',label='ground truth',lw=3)
plt.plot(forecast_steps, series_forecast_samples.T, lw=1,ls='--',color='black', alpha=0.45)
plt.plot(forecast_steps, series_forecast_mean, lw=2, ls='--', color='blue',label='forecast')
plt.legend(loc=2,prop={'size': 14})
plt.title('Sales Forecast Next 12 Weeks')
plt.show()

plt.figure(figsize=(10,7))
plt.plot(np.linspace(0,len(X0),len(X0)+12),np.concatenate([X0,Y0],axis=0),color='red',label='ground truth',lw=3)
plt.plot(forecast_steps, series_forecast_samples.T, lw=1,ls='--',color='black', alpha=0.45)
#plt.plot(np.array(list(np.linspace(0,len(X0),len(X0)+12))*10).reshape(-1,144), np.concatenate([np.array(list(X0.T[0])*10).reshape(10,-1).T,series_forecast_samples.T],axis=0).T, lw=1,ls='--',color='black', alpha=0.45)
plt.plot(forecast_steps, series_forecast_mean, lw=2, ls='--', color='blue',label='forecast')
plt.legend(loc=2,prop={'size': 14})
plt.title('Sales Forecast Next 12 Weeks')
plt.show()
