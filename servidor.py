import os
import random
import requests
import json
from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote
from whitenoise import WhiteNoise
from flask_migrate import Migrate

# --- INICIALIZAÇÃO E CONFIGURAÇÃO ---
app = Flask(__name__, template_folder='templates', static_folder='static')
app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/')

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///game_data.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# --- MODELO DO BANCO DE DADOS ---
class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), nullable=False)
    wins = db.Column(db.Integer, default=0)
    appearances = db.Column(db.Integer, default=0)

    def to_dict(self):
        approval = int((self.wins / self.appearances) * 100) if self.appearances > 0 else 0
        return {"id": self.id, "approval": approval}


# --- TRADUÇÕES ---
translations = {
    "pt": {"lang_code": "pt-br", "start_game": "▶ Iniciar Jogo", "next_round": "Próxima Rodada",
           "approval_of": "Aprovação de", "vs": "VS", "approval_error": "Aprovação: Tente Novamente"},
    "en": {"lang_code": "en", "start_game": "▶ Start Game", "next_round": "Next Round",
           "approval_of": "Approval Rating", "vs": "VS", "approval_error": "Approval Rating: Try Again Later"},
    "es": {"lang_code": "es", "start_game": "▶ Iniciar Juego", "next_round": "Siguiente Ronda",
           "approval_of": "Índice de Aprobación", "vs": "VS",
           "approval_error": "Índice de Aprobación: Inténtalo más tarde"}
}

# --- SUA CURADORIA DE ARTISTAS FINAL ---
ARTISTAS_ROCK = [
    ("The Beatles", 15), ("Queen", 14), ("The Rolling Stones", 7),
    ("Green Day", 6), ("Elvis Presley", 6), ("Pink Floyd", 7),
    ("Imagine Dragons", 12), ("Metallica", 8), ("AC/DC", 7),
    ("Guns N' Roses", 4), ("Bon Jovi", 4), ("Iron Maiden", 4),
    ("Red Hot Chili Peppers", 4), ("Linkin Park", 4), ("Boston", 3),
    ("Survivor", 2), ("Tame Impala", 3), ("Nirvana", 3),
    ("Lynyrd Skynyrd", 3), ("Aerosmith", 5), ("System Of A Down", 5),
    ("Radiohead", 4), ("Foo Fighters", 5), ("Led Zeppelin", 4),
    ("blink-182", 4), ("Creed", 4), ("Dire Straits", 3),
    ("U2", 4), ("Journey", 4), ("Nickelback", 3),
    ("ZZ Top", 2), ("Cutting Crew", 1), ("The Goo Goo Dolls", 1),
    ("Van Halen", 2), ("Def Leppard", 2), ("Keane", 2),
    ("Kansas", 2), ("Yes", 2), ("Men At Work", 2), ("Kenny Loggins", 2),
    ("DragonForce", 1), ("Simple Plan", 3), ("Eagles", 2)
]
ARTISTAS_POP = [
    ("Michael Jackson", 15), ("Madonna", 8), ("Elton John", 8),
    ("The Weeknd", 8), ("Taylor Swift", 10), ("Coldplay", 8),
    ("Billie Eilish", 11), ("Lana Del Rey", 9), ("Sabrina Carpenter", 8),
    ("Ariana Grande", 10), ("Bruno Mars", 12), ("Billy Joel", 6),
    ("Black Eyed Peas", 9), ("Phil Collins", 4), ("Lady Gaga", 5),
    ("Adele", 5), ("Prince", 3), ("Bee Gees", 4),
    ("Earth, Wind & Fire", 3), ("PSY", 2), ("Luis Fonsi", 2),
    ("Gotye", 1), ("Rick Astley", 2), ("Foster the People", 1),
    ("OMC", 1), ("Carly Rae Jepsen", 2), ("Haddaway", 1),
    ("Lou Bega", 1), ("Soft Cell", 1), ("Chumbawamba", 1),
    ("Natalie Imbruglia", 1), ("Passenger", 1), ("Daniel Powter", 1),
    ("Semisonic", 1), ("Artemas", 1), ("Dead or Alive", 1),
    ("BTS", 5), ("BLACKPINK", 5), ("One Direction", 10),
    ("Backstreet Boys", 5), ("OneRepublic", 8), ("Jason Mraz", 5),
    ("Owl City", 3), ("Gloria Gaynor", 3)
]
ARTISTAS_ELETRONICA = [
    ("Alan Walker", 7), ("Marshmello", 9), ("Calvin Harris", 10),
    ("Avicii", 7), ("David Guetta", 8), ("Daft Punk", 3),
    ("MGMT", 3), ("Eiffel 65", 1), ("Darude", 1), ("Gigi D'Agostino", 2)
]
ARTISTAS_RAP = [
    ("Eminem", 8), ("Travis Scott", 7), ("Tyler, The Creator", 7),
    ("Drake", 6), ("J. Cole", 6), ("Lil Wayne", 6),
    ("Kendrick Lamar", 5), ("Kanye West", 3), ("Future", 3),
    ("A$AP Rocky", 4), ("Vanilla Ice", 1), ("Juice WRLD", 6)
]
ARTISTAS_JAPONES = [
    ("Linked Horizon", 2),
    ("KANA-BOON", 1),
    ("YOASOBI", 2)
]
ARTISTAS_NCS = [
    ("NoCopyrightSounds", 15)
]
TODOS_OS_ARTISTAS = ARTISTAS_ROCK + ARTISTAS_POP + ARTISTAS_ELETRONICA + ARTISTAS_RAP + ARTISTAS_JAPONES + ARTISTAS_NCS

# --- FUNCIONALIDADE DE BLOCKLIST ---
ARTISTAS_BLOQUEADOS = [
    "sexyy red",
    "charli xcx"
]
# ------------------------------------

# --- LÓGICA DE CARREGAMENTO DE MÚSICAS ---
MASTER_SONG_LIBRARY = []
try:
    print("Iniciando curadoria musical...")
    temp_tracks = []
    for artist_name, limit in TODOS_OS_ARTISTAS:
        encoded_artist = quote(artist_name)
        search_url = f"https://api.deezer.com/search/artist?q={encoded_artist}"
        response = requests.get(search_url)
        if response.status_code != 200: continue
        artist_data = response.json().get("data", [])
        if not artist_data: continue
        artist_id = artist_data[0]['id']
        top_tracks_url = f"https://api.deezer.com/artist/{artist_id}/top?limit={limit}"
        response = requests.get(top_tracks_url)
        if response.status_code != 200: continue
        top_tracks_data = response.json().get("data", [])
        valid_tracks = [track for track in top_tracks_data if track.get("preview")]
        temp_tracks.extend(valid_tracks)

    MASTER_SONG_LIBRARY = list({track['id']: track for track in temp_tracks}.values())
    print(f"Operação concluída. {len(MASTER_SONG_LIBRARY)} músicas únicas carregadas.")

except Exception as e:
    print(f"Ocorreu um erro durante a inicialização: {e}")


# --- ROTAS DA API ---
@app.route('/')
def serve_index():
    lang_header = request.accept_languages.best_match(translations.keys())
    lang_code = lang_header if lang_header else "en"
    selected_translations = translations.get(lang_code, translations["en"])
    return render_template('musical.html', texts=selected_translations)


@app.route('/get-songs')
def get_songs():
    if not MASTER_SONG_LIBRARY or len(MASTER_SONG_LIBRARY) < 2:
        return jsonify({"error": "Biblioteca de músicas principal está vazia."}), 500

    while True:
        # LÓGICA DE ALEATORIEDADE PURA (COM REPOSIÇÃO)
        musicas_escolhidas = random.sample(MASTER_SONG_LIBRARY, 2)

        # VERIFICAÇÃO DA BLOCKLIST
        musica1_artista = musicas_escolhidas[0]['artist']['name'].lower()
        musica2_artista = musicas_escolhidas[1]['artist']['name'].lower()

        # Checa se os artistas não estão bloqueados E se as músicas são diferentes
        if musica1_artista not in ARTISTAS_BLOQUEADOS and \
                musica2_artista not in ARTISTAS_BLOQUEADOS and \
                musicas_escolhidas[0]['id'] != musicas_escolhidas[1]['id']:
            break  # Encontramos um par válido, então saímos do loop

    musicas_formatadas = []
    for track in musicas_escolhidas:
        musicas_formatadas.append({
            "id": track['id'], "title": track['title'], "artist": track['artist']['name'],
            "cover": track['album']['cover_medium'], "preview": track['preview']
        })
    return jsonify(musicas_formatadas)


@app.route('/vote', methods=['POST'])
def vote():
    data = request.json
    winner_id, loser_id = data.get('winner_id'), data.get('loser_id')
    winner_title, winner_artist = data.get('winner_title'), data.get('winner_artist')
    loser_title, loser_artist = data.get('loser_title'), data.get('loser_artist')
    if not all([winner_id, loser_id, winner_title, winner_artist, loser_title, loser_artist]):
        return jsonify({"error": "Dados incompletos"}), 400

    # Lógica de banco de dados robusta para o ambiente de produção
    with app.app_context():
        winner_db = Song.query.get(winner_id)
        if not winner_db:
            winner_db = Song(id=winner_id, title=winner_title, artist=winner_artist, wins=0, appearances=0)
            db.session.add(winner_db)
        loser_db = Song.query.get(loser_id)
        if not loser_db:
            loser_db = Song(id=loser_id, title=loser_title, artist=loser_artist, wins=0, appearances=0)
            db.session.add(loser_db)

        winner_db.wins += 1
        winner_db.appearances += 1
        loser_db.appearances += 1

        response_data = {
            str(winner_id): winner_db.to_dict(),
            str(loser_id): loser_db.to_dict()
        }

        db.session.commit()

        return jsonify(response_data)

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Cria o banco de dados de teste local se ele não existir
    app.run(port=5000, debug=True)
