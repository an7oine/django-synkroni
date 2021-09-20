# -*- coding: utf-8 -*-

import asyncio
import json
# from types import SimpleNamespace

from asgiref.sync import sync_to_async

from django.utils.functional import (
  # cached_property,
  classproperty,
)
from django.views.generic.detail import SingleObjectMixin

from .mallit import SynkronoituvaMalli
from .websocket import WebsocketYhteys


class Synkroni(SingleObjectMixin, WebsocketYhteys):
  '''
  Synkronoitu datayhteys selaimen ja tietokantaan tallennetun JSON-puun välillä.

  JSON-protokolla poimitaan tietomallin `data`-kentän määritysten mukaan.

  Alkutilanteessa data on `{"id": ...}`.
  '''

  # Tietokantamalli, jonka tietty, yksittäinen rivi toimii
  # tietovarastona, johon selain synkronoidaan.
  model = SynkronoituvaMalli

  # Tiedot synkronoidaan myös selaimelta palvelimelle päin.
  kaksisuuntainen = True

  async def suorita_toiminto(self, **kwargs):
    raise NotImplementedError

  @classproperty
  def json_koodain(cls):
    # pylint: disable=no-self-argument
    return cls.model._meta.get_field('data').encoder

  @classproperty
  def json_latain(cls):
    # pylint: disable=no-self-argument
    return cls.model._meta.get_field('data').decoder

  @property
  def data_alkutilanne(self):
    return {'id': self.object.pk}

  #@cached_property
  #def data(self):
  #  '''
  #  Tarjotaan data sanakirjan sijaan nimiavaruutena:
  #  self.data.xyz = 'abc' jne.
  #  '''
  #  return SimpleNamespace(**self.object.data)
  #  # def data

  async def kasittele_saapuva_sanoma(self, request, sanoma):
    ''' Toteuta saapuva muutos self.data.__dictiä__ vasten. '''
    if 'komento_id' not in sanoma:
      sanoma = sanoma if isinstance(sanoma, list) else [sanoma]
      # pylint: disable=no-value-for-parameter
      # pylint: disable=too-many-function-args
      self.json_paikkain(sanoma).apply(
        self.data, #.__dict__,
        in_place=True
      )
    else:
      await super().kasittele_saapuva_sanoma(request, sanoma)
    # async def kasittele_saapuva_sanoma

  async def _websocket(self, request, *args, **kwargs):
    '''
    Alusta self.object.

    Lähetä alkuhetken data, jos sitä on pyydetty
    CSRF-kättelyn yhteydessä.

    Vastaanota ja toteuta saapuvat JSON-paikkaukset.

    Tallenna data yhteyden katkettua.
    '''
    # pylint: disable=attribute-defined-outside-init
    # pylint: disable=no-member
    self.object = await sync_to_async(self.get_object)()

    if self._websocket_kattely.get('uusi'):
      await self.data_paivitetty(
        self.data_alkutilanne,
        self.data, #.__dict__,
      )

    try:
      while True:
        sanoma = await request.receive()
        if set(sanoma) == {'n', 'o'}:
          kaaritty_sanoma = sanoma['o']
          while sanoma['n'] > 0:
            sanoma = await request.receive()
            assert set(sanoma) == {'n', 'o'}
            kaaritty_sanoma += sanoma['o']
          sanoma = json.loads(
            kaaritty_sanoma,
            cls=self.json_latain
          )
        await self.kasittele_saapuva_sanoma(request, sanoma)
        # while True

    finally:
      # Tallenna data automaattisesti ennen yhteyden katkaisua.
      self.object.data = self.data #.__dict__
      await asyncio.shield(sync_to_async(self.object.save)())
    # async def websocket

  # class Synkroni
