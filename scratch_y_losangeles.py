import pandas as pd
import os

df = pd.read_csv('data/dataset_losangeles.csv')
# Wyciągamy kolumny
df_y = df[['Date', 'Max_Temp', 'Min_Temp', 'Avg_Temp']].copy()

# Zmieniamy nazwy na zgodne z y_miami.csv
df_y = df_y.rename(columns={
    'Date': 'date',
    'Max_Temp': 'temperature_max',
    'Min_Temp': 'temperature_min',
    'Avg_Temp': 'temperature_mean'
})

# Opcjonalnie: Konwersja na Fahrenheity (C * 1.8 + 32)
df_y['temperature_max'] = df_y['temperature_max'] * 1.8 + 32
df_y['temperature_min'] = df_y['temperature_min'] * 1.8 + 32
df_y['temperature_mean'] = df_y['temperature_mean'] * 1.8 + 32

os.makedirs('y_data_aws', exist_ok=True)
df_y.to_csv('y_data_aws/y_losangeles.csv', index=False)
print("Pomyślnie wygenerowano y_data_aws/y_losangeles.csv")
