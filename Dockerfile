# Gunakan image Python versi slim sebagai dasar
FROM python:3.9-slim

# Set direktori kerja di dalam container
WORKDIR /code

# Salin file requirements dulu dan install dependensi
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Salin semua sisa file proyek ke dalam container
COPY . /code

# Perintah untuk menjalankan aplikasi saat container dimulai
# Hugging Face menggunakan port 7860 secara default
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
