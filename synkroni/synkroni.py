# -*- coding: utf-8 -*-

import asyncio
import functools
import json
import traceback
from types import SimpleNamespace

from asgiref.sync import sync_to_async

from django.utils.functional import (
  cached_property,
  classproperty,
)
from django.views.generic.detail import SingleObjectMixin

from pistoke.nakyma import WebsocketNakyma
from pistoke.tyokalut import csrf_tarkistus, json_viestiliikenne

from jsonpatch import JsonPatch, multidict

from .mallit import SynkronoituvaMalli


class Synkroni(SingleObjectMixin, WebsocketNakyma):

  model = SynkronoituvaMalli

  data_alkutilanne = {}

  async def suorita_komento(self, **kwargs):
    raise NotImplementedError


  @classproperty
  def json_koodain(cls):
    # pylint: disable=no-self-argument
    return cls.model._meta.get_field('data').encoder

  @classproperty
  def json_latain(cls):
    # pylint: disable=no-self-argument
    return cls.model._meta.get_field('data').decoder

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

  @classmethod
  def __init_subclass__(cls, *args, **kwargs):
    super().__init_subclass__(*args, **kwargs)
    cls.websocket = json_viestiliikenne(
      cls.websocket,
      loads={'cls': cls.json_latain},
      dumps={'cls': cls.json_koodain},
    )
    # def __init_subclass__

  def __init__(self, *args, **kwargs):
    # pylint: disable=unidiomatic-typecheck
    if type(self) is __class__:
      raise TypeError('Synkroni-luokka on abstrakti!')
    super().__init__(*args, **kwargs)
    # def __init__

  @cached_property
  def data(self):
    return SimpleNamespace(**self.object.data)
    # def data

  async def data_paivitetty(self, vanha_data, uusi_data):
    # pylint: disable=no-member
    muutos = self.json_paikkain.from_diff(
      vanha_data, uusi_data
    ).patch
    assert isinstance(muutos, (list, dict))
    if muutos:
      await self.request.send(muutos)
    # async def data_paivitetty

  async def kasittele_saapuva_sanoma(self, request, sanoma):
    if 'komento_id' in sanoma:
      # Komento.
      try:
        vastaus = await self.suorita_komento(**sanoma)
      # pylint: disable=broad-except
      except Exception as exc:
        traceback.print_exc()
        await request.send({
          'virhe': str(exc),
        })
      else:
        if vastaus is not None:
          await request.send({
            'komento_id': sanoma['komento_id'],
            **vastaus
          })

    else:
      # Json-paikkaus.
      sanoma = sanoma if isinstance(sanoma, list) else [sanoma]
      # pylint: disable=no-value-for-parameter
      # pylint: disable=too-many-function-args
      self.json_paikkain(sanoma).apply(
        self.data.__dict__, in_place=True
      )
    # async def kasittele_saapuva_sanoma

  # Toteutetaan __init_subclass__-metodissa.
  #@json_viestiliikenne
  @csrf_tarkistus(
    csrf_avain='csrfmiddlewaretoken',
    virhe_avain='virhe'
  )
  async def websocket(self, request, *args, **kwargs):
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
        self.data.__dict__,
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
      self.object.data = self.data.__dict__
      await asyncio.shield(sync_to_async(self.object.save)())
    # async def websocket

  # class Synkroni
