# File: main.py

# 1. IMPORT LIBRARY
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from datetime import datetime
import yfinance as yf
import pandas as pd
import numpy as np
from prophet import Prophet
from fastapi.middleware.cors import CORSMiddleware

# 2. INISIALISASI APLIKASI FASTAPI
app = FastAPI(
    title="Stock Risk & Forecast API",
    description="API untuk analisis risiko portfolio dan peramalan harga saham."
)

# --- REVISI 1: Tambahkan Middleware CORS ---
origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    # PASTE URL FORWARDED DARI FRONTEND ANDA DI SINI
    "https://psychic-goldfish-jvvvxjrwgp9hg56-8080.app.github.dev", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Izinkan semua method (GET, POST, dll)
    allow_headers=["*"], # Izinkan semua header
)
# --- AKHIR REVISI 1 ---

# 3. KUMPULKAN FUNGSI INTI (Versi Terbaru yang Sudah Diperbaiki)
def get_stock_data(tickers: List[str], start_date: str, end_date: str):
    try:
        # Langsung ambil data 'Close'. yfinance akan mengembalikan DataFrame
        # baik untuk satu maupun banyak ticker.
        stock_data = yf.download(tickers, start=start_date, end=end_date)['Close']

        # Blok 'if len(tickers) == 1:' yang lama sudah tidak diperlukan dan dihapus.
        # Jika yfinance hanya mengembalikan satu Series (kasus langka),
        # baris berikutnya akan mengubahnya jadi DataFrame secara otomatis.
        if isinstance(stock_data, pd.Series):
             stock_data = stock_data.to_frame(name=tickers[0])

        return stock_data.dropna()
    except Exception as e:
        print(f"!!! TERJADI ERROR DI get_stock_data: {e}, Tickers: {tickers}")
        return None

def calculate_risk_metrics(price_data: pd.DataFrame):
    """Menghitung metrik risiko untuk portfolio dengan ASUMSI BOBOT SAMA."""
    daily_returns = price_data.pct_change().dropna()
    num_assets = len(price_data.columns)
    weights = np.array([1/num_assets] * num_assets)
    portfolio_returns = daily_returns.dot(weights)
    
    expected_return = portfolio_returns.mean() * 252
    volatility = portfolio_returns.std() * np.sqrt(252)
    sharpe_ratio = expected_return / volatility if volatility != 0 else 0
    
    return {
        "expected_annual_return": expected_return,
        "annual_volatility": volatility,
        "sharpe_ratio": sharpe_ratio
    }

def get_forecast(ticker: str, price_data: pd.DataFrame, forecast_horizon: int):
    """Membuat prediksi dan mengembalikan DataFrame forecast DAN modelnya."""
    df_prophet = price_data[[ticker]].reset_index()
    df_prophet.columns = ['ds', 'y']
    
    model = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=True)
    model.fit(df_prophet)
    
    future = model.make_future_dataframe(periods=forecast_horizon)
    forecast = model.predict(future)
    
    # Mengubah format tanggal agar bisa dikirim sebagai JSON
    forecast['ds'] = forecast['ds'].dt.strftime('%Y-%m-%d')
    
    # Mengembalikan DUA nilai, sesuai revisi Anda
    return forecast, model

# 4. DEFINISIKAN MODEL REQUEST (INPUT DARI USER) - Tidak ada perubahan
class RiskRequest(BaseModel):
    tickers: List[str] = ['BBCA.JK', 'TLKM.JK']
    start_date: str = '2020-01-01'
    end_date: str = datetime.now().strftime('%Y-%m-%d')

class ForecastRequest(BaseModel):
    ticker: str = 'BBCA.JK'
    start_date: str = '2020-01-01'
    end_date: str = datetime.now().strftime('%Y-%m-%d')
    forecast_horizon: int = 30



# 5. BUAT ENDPOINT API (Dengan Penyesuaian)
@app.post("/calculate-risk")
def calculate_risk_endpoint(request: RiskRequest):
    price_data = get_stock_data(request.tickers, request.start_date, request.end_date)
    if price_data is None or price_data.empty:
        return {"error": "Tidak dapat mengambil data saham. Periksa kembali ticker."}
    
    risk_metrics = calculate_risk_metrics(price_data)
    return risk_metrics

@app.post("/get-forecast")
def get_forecast_endpoint(request: ForecastRequest):
    price_data = get_stock_data([request.ticker], request.start_date, request.end_date)
    if price_data is None or price_data.empty:
        return {"error": "Tidak dapat mengambil data saham. Periksa kembali ticker."}

    # --- INI BAGIAN YANG BERUBAH ---
    # Kita panggil fungsi yang mengembalikan 2 nilai
    # Tapi kita hanya butuh yang pertama (forecast_data) untuk dikirim ke frontend
    # _ (underscore) adalah konvensi di Python untuk variabel yang nilainya kita abaikan
    forecast_data, _ = get_forecast(request.ticker, price_data, request.forecast_horizon)
    
    # Kita hanya mengirim data forecast yang sudah bersih
    final_forecast_data = forecast_data[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
    
    # Konversi DataFrame ke format JSON yang bisa dikirim
    return final_forecast_data.to_dict('records')