import pandas as pd
from sklearn.discriminant_analysis import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
import numpy as np
import mysql.connector

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'bp',
    'port': 1111
}

connection = mysql.connector.connect(**db_config)
cursor = connection.cursor()

sql = """
SELECT 
    f.price, f.area, f.type, f.after_reconstruction, f.atm, f.balcony, f.brick, 
    f.bus_public_transport, f.candy_shop, f.cellar, f.collective, f.drugstore, f.elevator, 
    f.furnished, f.garage, f.in_construction, f.kindergarten, f.loggia, f.medic, f.metro, 
    f.movies, f.natural_attraction, f.new_building, f.not_furnished, f.panel, f.parking_lots, 
    f.partly_furnished, f.personal, f.playground, f.post_office, f.restaurant, f.school, f.shop, 
    f.sightseeing, f.small_shop, f.sports, f.state, f.tavern, f.terrace, f.theater, f.train, f.tram, f.vet
FROM 
    byty_najem f
JOIN (
    SELECT 
        hash_id, MIN(id) as min_id
    FROM 
        byty_najem
    GROUP BY 
        hash_id
) AS x ON f.id = x.min_id;

"""

data = pd.read_sql_query(sql, connection)


dolni_hranice = data['price'].quantile(0.1)
horni_hranice = data['price'].quantile(0.9)

# Vyloučení záznamů, jejichž cena se nachází v dolní a horní kvantilové hranici
data = data[(data['price'] > dolni_hranice) & (data['price'] < horni_hranice)]


# Ošetření nečíslných hodnot
data['area'] = pd.to_numeric(data['area'], errors='coerce')
data['price'] = pd.to_numeric(data['price'], errors='coerce')

# Definování numerických sloupců
numericke_sloupce = ['area'] + [  # Seznam binárních sloupců
    "after_reconstruction", "atm", "balcony", "brick", "bus_public_transport", 
    "candy_shop", "cellar", "collective", "drugstore", "elevator", "furnished", 
    "garage", "in_construction", "kindergarten", "loggia", "medic", "metro", 
    "movies", "natural_attraction", "new_building", "not_furnished", "panel", 
    "parking_lots", "partly_furnished", "personal", "playground", "post_office", 
    "restaurant", "school", "shop", "sightseeing", "small_shop", "sports", "state", 
    "tavern", "terrace", "theater", "train", "tram", "vet"]

# Vlastnosti a cílová proměnná
X = data.drop(['price'], axis=1) 
y = data['price']

# Transformátor numerických sloupců - škálování
numerical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='constant')),
    ('scaler', StandardScaler())
])

# Transformátor kategoriálních sloupců - One-Hot Encoding
categorical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='most_frequent')),
    ('onehot', OneHotEncoder(handle_unknown='ignore'))
])

# Definování kategoriálních sloupců
kategorialni_sloupce = ["type"] 

# Definiování numerických sloupců
numericke_sloupce = ['area'] + [  # Seznam binárních sloupců
    "after_reconstruction", "atm", "balcony", "brick", "bus_public_transport", 
    "candy_shop", "cellar", "collective", "drugstore", "elevator", "furnished", 
    "garage", "in_construction", "kindergarten", "loggia", "medic", "metro", 
    "movies", "natural_attraction", "new_building", "not_furnished", "panel", 
    "parking_lots", "partly_furnished", "personal", "playground", "post_office", 
    "restaurant", "school", "shop", "sightseeing", "small_shop", "sports", "state", 
    "tavern", "terrace", "theater", "train", "tram", "vet"]

# Předzpracování dat pomocí transformátorů
predzpracovani = ColumnTransformer(
    transformers=[
        ('numericke', StandardScaler(), numericke_sloupce),
        ('kategorialni', OneHotEncoder(), kategorialni_sloupce)
    ])

predzpracovani = ColumnTransformer(
    transformers=[
        ('num', numerical_transformer, numericke_sloupce),
        ('cat', categorical_transformer, kategorialni_sloupce)
])

# Definice modelu a klasifikátoru
model = RandomForestRegressor(n_estimators=100)

klasifikator = Pipeline(steps=[('predzpracovani', predzpracovani),
                      ('model', model)])

X_trenovaci, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1)

klasifikator.fit(X_trenovaci, y_train)

# Predikce nájmů pro testovací sadu
predikce = klasifikator.predict(X_test)

# Vyhodnocení modelu
print('MSE:', mean_squared_error(y_test, predikce))

def stredni_absolutni_procentualni_chyba(y_true, y_pred): 
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

# Určení střední absolutní procentuální chyby
mape = stredni_absolutni_procentualni_chyba(y_test, predikce)
print('MAPE:', mape)

print('R^2:', r2_score(y_test, predikce))

def stredni_absolutni_procentualni_chyba(y_true, y_pred): 
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

# Získání přístupu k modelu z klasifikátoru
model = klasifikator.named_steps['model']

# Získání důležitostí aspektů z modelu
dulezitost_aspektu = model.feature_importances_

# Získání názvů aspektů po transformaci
predzpracovani = klasifikator.named_steps['predzpracovani']

# Získání kategoriálních aspektů před One-Hot Encodingem
urcene_aspekty = predzpracovani.named_transformers_['cat'].named_steps['onehot'].get_feature_names_out(kategorialni_sloupce)

# numericke_sloupce obsahovalo jak numerické, tak binární aspekty
numericke_a_binarni_aspekty = numericke_sloupce

# Kombinace kategoriálních, numerických a binárních aspektů
vsechny_aspekty = np.concatenate([numericke_a_binarni_aspekty, urcene_aspekty])

# Spojení důležitosti a názvů aspektů do jednoho DataFramu
dulezitost_aspektu_df = pd.DataFrame({'feature': vsechny_aspekty, 'importance': dulezitost_aspektu}).sort_values(by='importance', ascending=False)

dulezitost_aspektu_df.to_csv("dulezitost.csv")