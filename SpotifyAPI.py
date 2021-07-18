import requests
import datetime
import base64
from urllib.parse import urlencode
import numpy as np


class SpotifyAPI(object):
    __client_id = None
    __client_secret = None

    access_token = None

    # время когда токен перестанет быть активным
    expires = datetime.datetime.now()

    # мин к-во баллов, которое нужно песне, чтобы точно подходить под тип
    point_min = 60

    # типы, которые можно использовать в методе get()
    get_types = ['albums', 'tracks', 'playlists', 'audio-features']
    # параметры песен, которые используются для типизации
    chars = ["danceability", "energy", "loudness", "tempo"]
    # max и min значения параметров (какие вообще возможны)
    # (всех, кроме темпа)
    MM_chars = [(0.0, 1.0), (0.0, 1.0), (-60, 0)]
    # для определения, для типа подходит высокий темп или нет
    type_tempo_high = {
        'before sleep': False,
        'for workout': True,
        'for a party': True}
    song_types = ['before sleep', 'for workout', 'for a party']

    type_params = {}

    GOOD_STATUS_CODE = 200

    def __init__(self, client_id, client_secret):
        self.__client_id = client_id
        self.__client_secret = client_secret
        i = 0
        # тут мы считаем из файла посчитанные min, max, mean параметров
        # (ниже будет)
        for type_ in self.song_types:
            a = np.loadtxt(f'{type_} MMM.txt')
            self.type_params[type_] = a
            i += 1

    def client_creds(self):
        return f"{self.__client_id}:{self.__client_secret}"

    # получение токена
    def get_access_token(self):
        token_url = "https://accounts.spotify.com/api/token"
        token_data = {
            "grant_type": "client_credentials"
        }
        client_creds_b64 = base64.b64encode(self.client_creds().encode())
        token_headers = {
            "Authorization": f"Basic {client_creds_b64.decode()}"
            # <base64 encoded client_id:client_secret>
        }
        # запрашиваем токен
        r = requests.post(token_url, data=token_data, headers=token_headers)
        # проверка, что токен получен
        valid_request = r.status_code == self.GOOD_STATUS_CODE

        if valid_request:
            token_response_data = r.json()
            now = datetime.datetime.now()
            self.access_token = token_response_data['access_token']
            expires_in = token_response_data['expires_in']  # seconds
            self.expires = now + datetime.timedelta(seconds=expires_in)
            return True
        else:
            return False

    # проверка необходимости получения нового токена
    def refresh_token(self):
        expires = self.expires
        now = datetime.datetime.now()
        if not self.access_token or expires < now:
            self.get_access_token()

    # поиск трека, альбома или исполнителя по названию (имени)
    def search(self, artist_name, track_name, album_name,
               search_type, limit=20, offset=0):
        self.refresh_token()

        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        endpoint = "https://api.spotify.com/v1/search"
        if search_type == 'track':
            data = urlencode(
                {"q": "artist:" + artist_name + " track:" + track_name,
                 "type": search_type,
                 "limit": limit,
                 "offset": offset},
                safe=":")
        elif search_type == 'artist':
            data = urlencode({"q": artist_name,
                              "type": search_type,
                              "limit": limit,
                              "offset": offset})
        else:
            data = urlencode({"q": album_name,
                              "type": search_type,
                              "limit": limit,
                              "offset": offset})

        lookup_url = f"{endpoint}?{data}"
        r = requests.get(lookup_url, headers=headers)

        if r.status_code != self.GOOD_STATUS_CODE:
            raise Exception(r.json()['error']['message'])

        return r.json()

    # получение информации о треке, плейлисте и т.д по его id
    def get(self, type_, id):
        self.refresh_token()
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        lookup_url = f"https://api.spotify.com/v1/{type_}/{id}"
        r = requests.get(lookup_url, headers=headers)

        if r.status_code != self.GOOD_STATUS_CODE:
            raise Exception((r.json()['error']['message'], r.status_code))
        return r.json()

    # получение информации по url конечной точки
    def get_by_url(self, lookup_url):
        self.refresh_token()
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        r = requests.get(lookup_url, headers=headers)

        if r.status_code != self.GOOD_STATUS_CODE:
            raise Exception((r.json()['error']['message'], r.status_code))
        return r.json()

    # проверка соответствия песни выбранному типу
    def check_track(self, track_id, type_):
        try:
            track_params = self.get('audio-features', track_id)
        except Exception:
            raise

        points = 0
        for i in range(len(self.chars) - 1):
            if self.type_params[type_][2][i] \
                    <= (self.MM_chars[i][1] + self.MM_chars[i][0]) / 2:
                if track_params[self.chars[i]] \
                        <= self.type_params[type_][2][i]:
                    points += 25
                elif track_params[self.chars[i]] \
                        <= self.type_params[type_][1][i]:
                    points += 12.5
                else:
                    points += 0
            else:
                if track_params[self.chars[i]] \
                        >= self.type_params[type_][2][i]:
                    points += 25
                elif track_params[self.chars[i]] \
                        >= self.type_params[type_][0][i]:
                    points += 12.5
                else:
                    points += 0

        if self.type_tempo_high[type_]:
            if track_params['tempo'] \
                    >= self.type_params[type_][2][len(self.chars) - 1]:
                points += 25
            elif track_params['tempo'] \
                    >= self.type_params[type_][0][len(self.chars) - 1]:
                points += 12.5
        else:
            if track_params['tempo'] \
                    <= self.type_params[type_][2][len(self.chars) - 1]:
                points += 25
            elif track_params['tempo'] \
                    <= self.type_params[type_][1][len(self.chars) - 1]:
                points += 12.5

        if points >= self.point_min:
            return (True, 1)
        elif points >= self.point_min / 2:
            return (True, 0)
        else:
            return (False, 0)
