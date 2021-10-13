# -*- coding: utf-8 -*-

import asyncio
import functools
import json
import traceback

from django.utils.functional import cached_property, classproperty
from django.utils.html import escape

from jsonpatch import JsonPatch, multidict

from pistoke.nakyma import WebsocketNakyma
from pistoke.tyokalut import csrf_tarkistus, json_viestiliikenne


class WebsocketYhteys(WebsocketNakyma):

  # Datan alkutilanne sellaisena kuin sekä palvelin että selain
  # sen näkevät.
  data_alkutilanne = {}

  # Synkronoidaanko myös selaimen tekemät muutokset palvelimelle?
  kaksisuuntainen = False

  # Data sellaisena, kuin se kullakin ajan hetkellä näkyy, niin
  # palvelimella kuin selaimellakin.
  @cached_property
  def data(self):
    return {}

  # Selaimelta saapuvan toiminnon toteutus palvelimen päässä.
  # Konkreettinen toteutus: ks. `Toiminnot`-saateluokka.
  async def suorita_toiminto(self, **kwargs):
    raise NotImplementedError

  # JSON-koodain ja -latain.
  json_koodain = json.JSONEncoder
  json_latain = json.JSONDecoder

  # JSON-tiedonsiirtoprotokolla.
  @classproperty
  def json_paikkain(cls):
    # pylint: disable=no-self-argument
    class JsonPaikkain(JsonPatch):
      json_dumper = staticmethod(functools.partial(
        json.dumps,
        cls=cls.json_koodain,
      ))
      json_loader = staticmethod(functools.partial(
        json.loads,
        cls=cls.json_latain,
        object_pairs_hook=multidict
      ))
      # class JsonPaikkain
    return JsonPaikkain
    # def json_paikkain

  def __init__(self, *args, **kwargs):
    '''
    Estetään tämän saateluokan suora yksilöinti.

    Alustetaan self.komennot: tyhjä joukko.
    '''
    # pylint: disable=unidiomatic-typecheck
    if type(self) is __class__:
      raise TypeError(f'{__class__} on abstrakti!')
    super().__init__(*args, **kwargs)
    self.komennot = set()
    # def __init__

  def data_alkutilanne_json(self):
    ''' Palauta JSON-muotoinen datan alkutilanne. '''
    return escape(self.json_koodain().encode(
      self.data_alkutilanne
    ))
    # def data_alkutilanne_json

  def websocket_protokolla_json(self):
    ''' Palauta JSON-muotoinen tuettujen protokollien luettelo. '''
    if not getattr(self.websocket, 'protokolla', None):
      return 'null'
    return escape(self.json_koodain().encode(
      self.websocket.protokolla
    ))
    # def websocket_protokolla_json

  async def data_paivitetty(self, vanha_data, uusi_data):
    ''' Vertaa vanhaa ja uutta dataa; lähetä muutokset selaimelle. '''
    # pylint: disable=no-member
    muutos = self.json_paikkain.from_diff(
      vanha_data, uusi_data
    ).patch
    assert isinstance(muutos, (list, dict))
    if muutos:
      await self.request.send(muutos)
    # async def data_paivitetty

  async def kasittele_komento(self, request, *, komento_id, **kwargs):
    try:
      vastaus = await self.suorita_toiminto(**kwargs)
    # pylint: disable=broad-except
    except Exception as exc:
      traceback.print_exc()
      await request.send({
        'virhe': str(exc),
      })
    else:
      if vastaus is not None:
        await request.send({
          'komento_id': komento_id,
          **vastaus
        })
        # if vastaus is not None
      # else
    # async def kasittele_komento

  async def kasittele_saapuva_sanoma(self, request, sanoma):
    ''' Käsittele selaimelta saapuva sanoma. '''
    if 'komento_id' in sanoma:
      # Komento: suorita taustalla.
      # Useat peräkkäin saapuvat komennot ajetaan samanaikaisesti.
      komento = asyncio.ensure_future(
        self.kasittele_komento(request, **sanoma)
      )
      self.komennot.add(komento)

    else:
      # Json-paikkaus: toteuta tässä.
      # Huomaa, että paikkaukset on toteutettava peräkkäin
      # saapumisjärjestyksessä, ei samanaikaisesti.
      sanoma = sanoma if isinstance(sanoma, list) else [sanoma]
      # pylint: disable=no-value-for-parameter
      # pylint: disable=too-many-function-args
      self.json_paikkain(sanoma).apply(
        self.data, in_place=True
      )
    # async def kasittele_saapuva_sanoma

  async def _websocket(self, request, *args, **kwargs):
    '''
    Vastaanota ja toteuta saapuvat JSON-paikkaukset ja komennot.

    Huomaa, että luku ja kirjoitus tapahtuu JSON-muodossa;
    tämän metodin suoritus on käärittävä `json_viestiliikenne`-
    funktion tuottamaan kääreeseen ajon aikana.
    '''
    try:
      while True:
        sanoma = await request.receive()
        await self.kasittele_saapuva_sanoma(request, sanoma)
        # while True
    finally:
      for kesken in self.komennot:
        kesken.cancel()
      await asyncio.gather(*self.komennot)
      # finally
    # async def _websocket

  async def websocket(self, request, *args, **kwargs):
    ''' JSON-ohjaimet valitaan pyyntökohtaisesti. '''
    # pylint: disable=no-self-argument, arguments-differ
    @json_viestiliikenne(
      # Käytetään luokkakohtaisesti määriteltyä JSON-protokollaa
      # viestinnässä selaimen kanssa.
      loads={'cls': self.json_latain},
      dumps={'cls': self.json_koodain},
    )
    @csrf_tarkistus(
      csrf_avain='csrfmiddlewaretoken',
      virhe_avain='virhe'
    )
    async def websocket(self, request, *args, **kwargs):
      # pylint: disable=protected-access
      return await self._websocket(request, *args, **kwargs)
      # async def websocket
    return await websocket(self, request, *args, **kwargs)
    # def websocket
  websocket.protokolla = 'django-synkroni'

  # class WebsocketYhteys
