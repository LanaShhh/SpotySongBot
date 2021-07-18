import requests
from SpotifyAPI import SpotifyAPI
import time
from urllib.parse import urlencode
import logging


logging.basicConfig(level=logging.INFO, filename='logs.txt', filemode='w')
class Bot(object):
    __token = None
    API_link = 'https://api.telegram.org/bot'
    offset = 0

    GOOD_STATUS_CODE = 200

    client = None

    def __init__(self):
        from data import token
        self.__token = token
        self.API_link = f"{self.API_link}{self.__token}"

        from data import client_id
        from data import client_secret

        self.client = SpotifyAPI(client_id=client_id,
                                 client_secret=client_secret)

    def req(self, command, params=None):
        link = ''
        if params:
            str_params = urlencode(params)
            link = f"{self.API_link}/{command}?{str_params}"
        else:
            link = f"{self.API_link}/{command}"

        r = requests.get(link)

        return r.json()

    def getUpdates(self):
        r = self.req('getUpdates', [('offset', self.offset)])
        self.offset = r['result'][-1]['update_id'] + 1

        logging.info('made request')

        for elem in r['result']:
            user_name = elem['message']['from']['first_name'] \
                        + ' ' \
                        + elem['message']['from']['last_name']
            chat_id = elem['message']['chat']['id']
            user_message = elem['message']['text']

            logging.info(f'analyse the message -- {user_message}')

            if (user_message == '/start'):
                text = f'Hi there, {user_name}! ' \
                       f'Read description, if you don`t know what to do ^_^'
                resp = self.req('sendMessage',
                                [('chat_id', chat_id), ('text', text)])
            elif (user_message[0:8] == '/analyse'):
                try:
                    track_id = user_message.split(' ')[1].split('/')[4][0:22]
                    logging.info(track_id)
                    track = self.client.get('tracks', track_id)
                except Exception:
                    text = f'It is not a track link, please, try again :('
                    resp = self.req('sendMessage',
                                    [('chat_id', chat_id), ('text', text)])
                    raise


                track_name = track['name']
                artists = ''
                for elem in track['artists']:
                    artists += ('\n' + elem['name'])

                text = f'Look, I have found something!'
                resp = self.req('sendMessage',
                                [('chat_id', chat_id), ('text', text)])
                text = f'Song: {track_name}'
                resp = self.req('sendMessage',
                                [('chat_id', chat_id), ('text', text)])
                text = f'Artists:' + '\n' + f'{artists}'
                resp = self.req('sendMessage',
                                [('chat_id', chat_id), ('text', text)])

                for type_ in self.client.song_types:
                    logging.info(f'analyse {type_}')
                    try:
                        ans = self.client.check_track(type_=type_,
                                                  track_id=track_id)
                    except Exception:
                        text = f'Sorry, I can not analyse this track ' \
                              f'(there is no required data about the track)'
                        resp = self.req('sendMessage',
                                        [('chat_id', chat_id), ('text', text)])
                        raise

                    text=f"{type_} : "

                    if ans[0]:
                        if ans[1]:
                            text += "YES!"
                        else:
                            text += "I am not sure..."
                    else:
                        text += 'NO :('

                    resp = self.req('sendMessage',
                                    [('chat_id', chat_id), ('text', text)])

                text = 'Ok, that is my opinion, give me another track!'
                resp = self.req('sendMessage',
                                [('chat_id', chat_id), ('text', text)])
            elif (user_message == '/help'):
                text = 'Write down: \n ' \
                       '/analyse LINK \n ' \
                       '(LINK is a song link from Spotify)'
                resp = self.req('sendMessage',
                                [('chat_id', chat_id), ('text', text)])
            else:
                text = 'Sorry, I don`t understand you :( ' \
                       'Please, write again what you want'
                resp = self.req('sendMessage',
                                [('chat_id', chat_id), ('text', text)])

    def session(self):
        while True:
            try:
                logging.info('try get messages.....')
                self.getUpdates()
                time.sleep(2)
            except Exception:
                time.sleep(1)
