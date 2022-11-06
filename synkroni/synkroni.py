# -*- coding: utf-8 -*-

import asyncio
import json

from asgiref.sync import sync_to_async

from django.utils.functional import (
  cached_property,
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

  Ensimmäisen synkronoinnin yhteydessä dataksi vaihtuu kuitenkin
  todellinen tietokantarivin sisältö.
  '''
  # pylint: disable=abstract-method

  # Tietokantamalli, jonka tietty, yksittäinen rivi toimii
  # tietovarastona, johon selain synkronoidaan.
  model = SynkronoituvaMalli

  # Tiedot synkronoidaan myös selaimelta palvelimelle päin.
  kaksisuuntainen = True

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

  @cached_property
  def data(self):
    '''
    Käsitellään synkronoitavan mallin dataa sellaisenaan.
    '''
    return self.object.data
    # def data

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

    if request._csrf_kattely.get('uusi'):
      await self.data_paivitetty(
        self.data_alkutilanne,
        self.data,
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
      await asyncio.shield(sync_to_async(self.object.save)())
    # async def _websocket

  # class Synkroni
