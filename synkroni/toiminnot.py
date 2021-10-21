# -*- coding: utf-8 -*-

import copy
import functools
import inspect


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
    raise ValueError('Tuntematon toiminto: ' + ', '.join(kwargs))
  # def toiminto


def muuttaa_tietoja(metodi):
  @functools.wraps(metodi)
  async def _metodi(self, *args, **kwargs):
    vanha_data = copy.deepcopy(self.data)
    try:
      return await _metodi.__wrapped__(self, *args, **kwargs)
    finally:
      await self.data_paivitetty(vanha_data, self.data)
  return _metodi
  # def muuttaa_tietoja


class Toiminnot:
  # data = None

  # async def data_paivitetty(self, vanha_data, uusi_data):
  #   raise NotImplementedError

  def _toiminto(self, *args, **kwargs):
    return toiminto(self, *args, **kwargs)
    # def _toiminto

  async def suorita_toiminto(self, **kwargs):
    if not kwargs:
      raise ValueError('Toiminnon tiedot puuttuvat: %r' % kwargs)
    _toiminto = self._toiminto(**kwargs)
    assert inspect.isawaitable(_toiminto)
    return await _toiminto
    # async def suorita_toiminto

  @toiminto
  async def yhteys_alustettu(self):
    ''' Yhteyskokeilu. '''
    return {}
    # async def yhteys_alustettu

  # class Toiminnot
