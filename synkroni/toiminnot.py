# -*- coding: utf-8 -*-

import asyncio
from contextlib import asynccontextmanager
import copy
import functools
import inspect
from time import time


def toiminto(*args, **kwargs):
  # pylint: disable=protected-access
  try: toiminto._toiminnot
  except AttributeError: toiminto._toiminnot = []
  if not kwargs:
    uusi_toiminto, = args
    toiminto._toiminnot.append(uusi_toiminto)
    return uusi_toiminto
  try:
    return next((
      metodi(
        *args,
        **kwargs[metodi.__name__]
      )
      for metodi in toiminto._toiminnot
      if metodi.__name__ in kwargs
    ))
  except StopIteration:
    # pylint: disable=raise-missing-from
    raise ValueError(
      f'Tuntematon toiminto: {", ".join(kwargs)}.'
      f' Käytössä ovat toiminnot {", ".join((t.__name__ for t in toiminto._toiminnot))}.'
    )
  # def toiminto


@asynccontextmanager
async def muuttaa_tietoja(self):
  '''
  Asynkroninen konteksti: lähettää muuttuneet tiedot selaimelle.

  Huomaa, että vain yksi muuttaa_tietoja-konteksti voi olla
  kerrallaan auki.
  '''
  async with muuttaa_tietoja.lukko:
    vanha_data = copy.deepcopy(self.data)
    yield
    await self.data_paivitetty(vanha_data, self.data)
  # def muuttaa_tietoja
muuttaa_tietoja.lukko = asyncio.Lock()


class Toiminnot:
  # data = None

  # async def data_paivitetty(self, vanha_data, uusi_data):
  #   raise NotImplementedError

  def _toiminto(self, *args, **kwargs):
    return toiminto(self, *args, **kwargs)
    # def _toiminto

  def mittaa_toiminnon_kesto(self, toiminto, kesto):
    pass

  async def suorita_toiminto(self, **kwargs):
    if not kwargs:
      raise ValueError('Toiminnon tiedot puuttuvat: %r' % kwargs)
    _toiminto = self._toiminto(**kwargs)
    assert inspect.isawaitable(_toiminto)
    alku = time()
    try:
      return await _toiminto
    finally:
      self.mittaa_toiminnon_kesto(_toiminto, time() - alku)
    # async def suorita_toiminto

  @toiminto
  async def yhteys_alustettu(self):
    ''' Yhteyskokeilu. '''
    return {}
    # async def yhteys_alustettu

  # class Toiminnot
