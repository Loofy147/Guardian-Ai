import pandas as pd
import numpy as np
import torch
from huggingface_hub import login
from transformers import TimeSeriesTransformerForPrediction
from gluonts.time_feature import time_features_from_frequency_str

class TimeSeriesPredictor:
    """
    A predictor that uses a pre-trained Hugging Face model for time-series forecasting.
    """

    def __init__(self, token: str, historical_demand: pd.DataFrame, prediction_length: int = 24):
        """
        Initializes the predictor, logs into Hugging Face Hub, and downloads a pre-trained model.

        Args:
            token (str): The Hugging Face Hub authentication token.
            historical_demand (pd.DataFrame): DataFrame with 'timestamp' and 'value' columns.
            prediction_length (int): The number of future time steps to predict.
        """
        login(token=token)

        self.model = TimeSeriesTransformerForPrediction.from_pretrained(
            "huggingface/time-series-transformer-finetuned-electricity-hourly"
        )
        self.prediction_length = prediction_length

        if not isinstance(historical_demand, pd.DataFrame) or 'value' not in historical_demand.columns:
            raise ValueError("historical_demand must be a pandas DataFrame with a 'value' column.")
        self.historical_demand = historical_demand

    def _prepare_input_data(self):
        """
        Prepares the historical data for the Transformer model.
        """
        series = self.historical_demand['value'].values

        # Normalize the series
        self.series_mean = np.mean(series)
        self.series_std = np.std(series)
        normalized_series = (series - self.series_mean) / self.series_std

        # Create time features for hourly frequency
        freq = "1h"
        time_feats = time_features_from_frequency_str(freq)

        timestamps = self.historical_demand['timestamp']
        time_series_features = np.vstack([feat(timestamps) for feat in time_feats])

        return {
            "past_values": torch.tensor(normalized_series, dtype=torch.float32).unsqueeze(0),
            "past_time_features": torch.tensor(time_series_features, dtype=torch.float32).unsqueeze(0),
        }

    def predict(self):
        """
        Generates a prediction and an uncertainty estimate based on the historical data
        provided during initialization.

        Returns:
            tuple[float, float]: A tuple containing the predicted value (mean of the forecast)
                                 and the uncertainty estimate (std dev of the forecast).
        """
        if self.historical_demand.empty or len(self.historical_demand['value']) == 0:
            return 0, 0

        # Prepare the data for the model
        model_input = self._prepare_input_data()

        # Run inference
        with torch.no_grad():
            outputs = self.model.generate(**model_input)

        # De-normalize the output
        forecast_values = outputs.sequences.numpy().squeeze()
        denormalized_forecast = forecast_values * self.series_std + self.series_mean

        # Use the mean of the forecast as the prediction and the std dev as the uncertainty
        prediction = np.mean(denormalized_forecast)
        uncertainty = np.std(denormalized_forecast)

        return prediction, uncertainty
