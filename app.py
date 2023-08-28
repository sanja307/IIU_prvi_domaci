
import os
import psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask, request

#prva tabela za sobe u kuci, za svaki red tabela ima jedinstveni identifikator sobe i naziv
CREATE_ROOMS_TABLE = (
    "CREATE TABLE IF NOT EXISTS rooms (id SERIAL PRIMARY KEY, name TEXT);"
)

#kreiramo drugu tabelu za temperature (nece se ponovo kreirati ako vec postoji) 
# koja ima spoljni kljuc ka tabeli ROOMS koji referencira room_id kolonu tabele ROOMS 
# to znaci da je svaka temperatura vezana za postojecu sobu putem njenog ID-a 
# na taj nacin su povezane temperature i sobe i mozemo da vidimo kolika je temperatura u kojoj sobi 
#ako se obrise soba, sve temperature vezane za tu sobu ce se takodje obrisati
CREATE_TEMPS_TABLE = """CREATE TABLE IF NOT EXISTS temperatures (room_id INTEGER, temperature REAL,
                         date TIMESTAMP, FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE);"""

#ova linija koda sluzi da unesemo sobu u tabelu ROOMS
#unosimo kolonu za ime (values su vrednosti imena) na osnovu koje se vraca id sobe nakon sto je ona dodata
INSERT_ROOM_RETURN_ID = "INSERT INTO rooms (name) VALUES (%s) RETURNING id;"

#ova linija koda sluzi da unesemo temperaturu u tabelu TEMPS
#room_id, temperature i date su kolone za koje zelimo da unesemo vrednosti
INSERT_TEMP = (
    "INSERT INTO temperatures (room_id, temperature, date) VALUES (%s, %s, %s);"
)

#ova linija koda prikazuje broj dana zabelezenih podataka o temperaturi
GLOBAL_NUMBER_OF_DAYS = (
    """SELECT COUNT(DISTINCT DATE(date)) AS days FROM temperatures;"""
)

#sada uzimamo prosecnu temperaturu kroz celu kucu
GLOBAL_AVG = """SELECT AVG(temperature) as average FROM temperatures;"""

load_dotenv()
url = os.getenv("DATABASE_URL")
connection = psycopg2.connect(url)
app = Flask(__name__)


#POST koristimo za dodavanje podataka
@app.post("/api/room")
def create_room():
    data = request.get_json()
    name = data["name"]
    #konekcija sa bazom
    with connection:
        #cursor je objekat koji nam dozvoljava da unesemo podatak u bazu
        with connection.cursor() as cursor:
            cursor.execute(CREATE_ROOMS_TABLE)
            cursor.execute(INSERT_ROOM_RETURN_ID, (name,))
            room_id = cursor.fetchone()[0]  #ima 2 reda, id i name, a mi pristupamo id-u

    return {"id": room_id, "message": f"Room {name} created."}, 201

#Sada ocekujemo od korisnika da unese naziv sobe, id sobe i datum kad je izmerena temperatura
#ako ne posalje datum, uzimamo trenutni
@app.post("/api/temperature")
def add_temp():
    data = request.get_json()
    temperature = data["temperature"]
    room_id = data["room"]
    try:
        date = datetime.strptime(data["date"], "%d/%m/%Y  %H:%M:%S") #datum u formatu: dan/mesec/godina sati:minuti:sekunde
    except KeyError:
        date = datetime.now(timezone.utc) #ako korisnik nije uneo datum

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_TEMPS_TABLE)
            cursor.execute(INSERT_TEMP, (room_id, temperature, date)) #tri vrednosti za svaku temperaturu koju unosimo u tabelu

    return {"message": " Temperature added."}, 201

#funkcija koja vraca podatak o prosecnoj temperaturi u celoj kuci i danima kada je ona merena
@app.get("/api/average")
def get_global_avg():
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(GLOBAL_AVG)
            average = cursor.fetchone()[0]  #fetchone pristupa prvom redu, a [0] prvoj koloni u tom redu
            cursor.execute(GLOBAL_NUMBER_OF_DAYS)
            days = cursor.fetchone()[0]

    return {"average": round(average, 2), "days": days}

@app.put("/api/temperature/<int:room_id>")
def update_temperature(room_id):
    data = request.get_json()
    new_temperature = data["temperature"]
    try:
        new_date = datetime.strptime(data["date"], "%d/%m/%Y  %H:%M:%S")
    except KeyError:
        new_date = datetime.now(timezone.utc)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE temperatures SET temperature = %s, date=%s WHERE room_id=%s", (new_temperature, new_date, room_id))
    
    return {"message": f"Temperature with ID {room_id} updated."}, 201