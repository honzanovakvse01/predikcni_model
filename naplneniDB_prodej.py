import re
import unicodedata
import requests
import pandas as pd
import mysql.connector
import joblib
from mysql.connector import Error

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'bp',
    'port': 1111
}

insert_prikaz = """
INSERT INTO byty_prodej (
    price, loc, area, type, after_reconstruction, atm, balcony, brick, bus_public_transport, candy_shop,
    cellar, collective, drugstore, elevator, furnished, garage, in_construction,
    kindergarten, loggia, medic, metro, movies, natural_attraction, new_building,
    not_furnished, panel, parking_lots, partly_furnished, personal, playground,
    post_office, restaurant, school, shop, sightseeing, small_shop, sports, state,
    tavern, terrace, theater, train, tram, vet, hash_id, predicted, oblast, img, seoLoc
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""

try:
    # Adresa API endpointu
    url = "https://www.sreality.cz/api/cs/v2/estates"

    # Hlavička požadavku
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "cs-CZ,cs;q=0.9",
        "sec-ch-ua": "\"Google Chrome\";v=\"113\", \"Chromium\";v=\"113\", \"Not-A.Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"macOS\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }

    # Volba parametrů
    params = {
        "category_main_cb": 1, # byty
        "category_type_cb": 1, # k prodeji
        "per_page": 200,  # 200 inzerátů najednou pro rychlejší fetching, zároveň ale bez zahlcení serveru
    }

    response = requests.get(url, headers=headers, params=params) # odeslání požadavku a následné uložení výsledku do proměnné response

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    vsechny_stitky = [
    'after_reconstruction', 'atm', 'balcony', 'brick', 'bus_public_transport',
    'candy_shop', 'cellar', 'collective', 'drugstore', 'elevator', 'furnished',
    'garage', 'in_construction', 'kindergarten', 'loggia', 'medic', 'metro',
    'movies', 'natural_attraction', 'new_building', 'not_furnished', 'panel',
    'parking_lots', 'partly_furnished', 'personal', 'playground', 'post_office',
    'restaurant', 'school', 'shop', 'sightseeing', 'small_shop', 'sports', 'state',
    'tavern', 'terrace', 'theater', 'train', 'tram', 'vet'
    ]  

    def transformace_loc(text):
        # Normalizování textu pro zbavení se speciálních znaků
        normalizovany_text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
        # Převod na malá písmena
        mala_pismena = normalizovany_text.lower()
        # Odstranění případného textu za (a včetně) čárkou - případné okresy
        bez_carky = mala_pismena.split(',')[0]
        # Nahrazení mezer pomlčkami
        text_s_carkama = bez_carky.replace(" ", "-")
        # Nahrazení více pomlaček po sobě jednou pomlčkou
        finalni_text = re.sub('-+', '-', text_s_carkama)
        finalni_text = finalni_text.split("-")[0]           
        return finalni_text
    
    def zjisteni_velikosti(text):
        # Využití regulárního výrazu pro nalezení jedné nebo více číslic doprovázené volitelnou mezerou a "m²"
        shoda = re.search(r'(\d+)\s*m²', text)
        if shoda:
            # Převod nalezené shody do číselného tvaru
            return int(shoda.group(1))
        else:
            return None
        
    def zjisteni_typu(text):
        # Využití regulárního výrazu pro nalezení typu půdorysu
        vzor = r'(\d+\+\d+|\d+\+kk|6 a více|atypické|pokoj)'
        # Nalezení vzoru v názvu inzerátu
        shoda = re.search(vzor, text)
        if shoda:
            return shoda.group(1)
        else:
            return None

    nacteny_model = joblib.load("predikcni_model.sav")

    def predikce(seznam_atributu):
        data_k_predikci = pd.DataFrame(seznam_atributu)

        #Odebrání sloupců id a hash_id
        data_k_predikci = data_k_predikci.iloc[1:-1].reset_index(drop=True)

        #Transpozice tabulky
        data_k_predikci = data_k_predikci.T

        seznam_sloupcu = [
            'loc', 'area', 'type', 'after_reconstruction', 'atm', 'balcony', 'brick', 'bus_public_transport', 'candy_shop', 'cellar',
            'collective', 'drugstore', 'elevator', 'furnished', 'garage', 'in_construction', 'kindergarten', 'loggia', 'medic', 'metro',
            'movies', 'natural_attraction', 'new_building', 'not_furnished', 'panel', 'parking_lots', 'partly_furnished', 'personal',
            'playground', 'post_office', 'restaurant', 'school', 'shop', 'sightseeing', 'small_shop', 'sports', 'state', 'tavern',
            'terrace', 'theater', 'train', 'tram', 'vet'
        ]

        #Reset indexu prvotního DataFramu
        data_k_predikci.reset_index(drop=True, inplace=True)
        
        #Pojmenování sloupců podle seznamu_sloupcu
        data_k_predikci.columns = seznam_sloupcu                
                
        predikovana_cena = nacteny_model.predict(data_k_predikci)
        print(predikovana_cena)
        return int(round(predikovana_cena[0]))

    params["page"] = 1

    while True:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            listings = data['_embedded']['estates']
            if not listings:
                break
            for listing in listings:
                # Ověření, zda se nejedná o byt v aukci
                if listing.get("is_auction"):
                    continue # přeskočení daného bytu

                # Nastavení výchozí hodnoty pro každý štítek na 0
                stitky = {hodnota: 0 for hodnota in vsechny_stitky}
                # Změna hodnota, pokud je u bytu daný štítek přítomen
                for obsazene_stitky in listing.get("labelsAll", []): # Kontrola všech obsažených štítků
                    for stitek in obsazene_stitky:
                        ocisteny_stitek = stitek.replace(" ", "_").replace("-", "_").lower()
                        if ocisteny_stitek in stitky: 
                            stitky[ocisteny_stitek] = 1
              
                # Vytvoření seznamu, který obsahuje veškeré potřebné atributy
                seznam_atributu = (
                    listing.get("price"),
                    transformace_loc(listing.get("locality")),
                    zjisteni_velikosti(listing.get("name")),
                    zjisteni_typu(listing.get("name")),
                    *stitky.values(),
                    listing.get("hash_id"),
                    predikce((listing.get("price"),
                    transformace_loc(listing.get("locality")),
                    zjisteni_velikosti(listing.get("name")),
                    zjisteni_typu(listing.get("name")),
                    *stitky.values(),
                    listing.get("hash_id"))),
                    listing.get("locality"),
                    listing.get("_links").get("images")[0]["href"],
                    listing.get("seo")["locality"]
                )
                
                # Vložení záznamu do databáze
                cursor.execute(insert_prikaz, seznam_atributu)
                connection.commit()
            params['page'] += 1
        else:
            break

except Error as e:
    print(f"Error: {e}")
