from django.forms.widgets import Media
from django.middleware.csrf import get_token

from django_sivumedia import (
  JSBool,
  JSMedia,
  Mediasaate,
)

from synkroni.websocket import WebsocketYhteys


class JsonPatch(Mediasaate):

  class Media:
    versio = '0.7.0'
    js = [
      f'https://cdn.jsdelivr.net'
      f'/gh/bruth/jsonpatch-js@{versio}/jsonpatch.js',
    ]
    # class Media

  # class JsonPatch


class SynkroniMedia(JsonPatch, WebsocketYhteys):
  # pylint: disable=function-redefined, abstract-method

  @property
  def media(self):
    if not self.request.websocket:
      raise RuntimeError('Websocket-toteutus vaaditaan!')

    return super().media + Media(
      js=[
        *((
          # Kaksisuuntainen tiedonsiirto edellyttää
          # JSON-patcherproxy-komentosarjan käyttöä.
          'https://cdn.jsdelivr.net'
          '/gh/Palindrom/JSONPatcherProxy@0.0.10'
          '/dist/jsonpatcherproxy.min.js',
        ) if self.kaksisuuntainen else ()),

        JSMedia(
          'synkroni/js/synkroni.js',
          **{
            'data-websocket': ''.join((
              self.request.websocket,
              self.request.path,
            )),
            'data-protokolla': (
              self.websocket_protokolla_json
            ),
            'data-kattely': {
              'csrfmiddlewaretoken': get_token(self.request),
              'uusi': JSBool(True)
            },
            'data-asetukset': {
              'paivitaKaikki': JSBool(self.paivita_kaikki)
            },
          },
        ),
      ]
    )
    # def media

  # class SynkroniMedia
