import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from keras.models import load_model
from django.shortcuts import render
from django.http import FileResponse
import datetime as dt
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
import os

# Load the model (ensure the model is in the correct path)
model = load_model('static/stock_dl_model.h5')

def index(request):
    if request.method == 'POST':
        stock = request.POST.get('stock', 'POWERGRID.NS')  # Default stock
        
        # Define stock data timeframe
        start = dt.datetime(2000, 1, 1)
        end = dt.datetime(2024, 10, 1)

        # Download stock data
        df = yf.download(stock, start=start, end=end)

        # Data descriptions
        data_desc = df.describe()

        # Calculate Exponential Moving Averages (EMA)
        ema20 = df.Close.ewm(span=20, adjust=False).mean()
        ema50 = df.Close.ewm(span=50, adjust=False).mean()
        ema100 = df.Close.ewm(span=100, adjust=False).mean()
        ema200 = df.Close.ewm(span=200, adjust=False).mean()

        # Data splitting and scaling
        data_training = pd.DataFrame(df['Close'][0:int(len(df) * 0.70)])
        data_testing = pd.DataFrame(df['Close'][int(len(df) * 0.70):])
        scaler = MinMaxScaler(feature_range=(0, 1))
        data_training_array = scaler.fit_transform(data_training)

        # Prepare data for predictions
        past_100_days = data_training.tail(100)
        final_df = pd.concat([past_100_days, data_testing], ignore_index=True)
        input_data = scaler.fit_transform(final_df)

        x_test, y_test = [], []
        for i in range(100, input_data.shape[0]):
            x_test.append(input_data[i - 100:i])
            y_test.append(input_data[i, 0])
        x_test, y_test = np.array(x_test), np.array(y_test)

        # Predict prices
        y_predicted = model.predict(x_test)

        # Rescale predictions
        scale_factor = 1 / scaler.scale_[0]
        y_predicted = y_predicted * scale_factor
        y_test = y_test * scale_factor

        # Save plots
        plots = [
            {
                'title': "Closing Price vs Time (20 & 50 Days EMA)",
                'path': "static/ema_20_50.png",
                'data': [(df.Close, 'y', 'Closing Price'), (ema20, 'g', 'EMA 20'), (ema50, 'r', 'EMA 50')],
            },
            {
                'title': "Closing Price vs Time (100 & 200 Days EMA)",
                'path': "static/ema_100_200.png",
                'data': [(df.Close, 'y', 'Closing Price'), (ema100, 'g', 'EMA 100'), (ema200, 'r', 'EMA 200')],
            },
            {
                'title': "Prediction vs Original Trend",
                'path': "static/stock_prediction.png",
                'data': [(y_test, 'g', 'Original Price'), (y_predicted, 'r', 'Predicted Price')],
            },
        ]

        for plot in plots:
            fig, ax = plt.subplots(figsize=(12, 6))
            for d, c, label in plot['data']:
                ax.plot(d, c, label=label)
            ax.set_title(plot['title'])
            ax.legend()
            fig.savefig(plot['path'])  # Save the plot
            plt.close(fig)  # Explicitly close the figure to release resources

        # Save dataset
        csv_file_path = f"static/{stock}_dataset.csv"
        df.to_csv(csv_file_path)

        # Render the template
        return render(request, 'index.html', {
            'plot_paths': [plot['path'] for plot in plots],
            'data_desc': data_desc.to_html(classes='classes="table-auto border-collapse border border-gray-400 text-sm text-center"'),
            'dataset_link': csv_file_path.split('/')[-1],
        })

    return render(request, 'index.html')

def download_file(request, filename):
    filepath = os.path.join('static', filename)
    return FileResponse(open(filepath, 'rb'), as_attachment=True)
