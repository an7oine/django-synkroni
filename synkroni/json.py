# -*- coding: utf-8 -*-

from decimal import Decimal
import json


class JSONKoodain(json.JSONEncoder):
  ''' Koodataan desimaaliluvut desimaaliesityksenä. '''
  class Desimaali(float):
    def __init__(self, value):
      self._value = value
    def __repr__(self):
      return str(self._value)
  def default(self, o):
    if isinstance(o, Decimal):
      return self.Desimaali(o)
    return super().default(o)
    # def default
  # class JSONKoodain


class JSONLatain(json.JSONDecoder):
  ''' Tulkitaan desimaaliesitykset desimaalilukuina. '''
  def __init__(self, *args, **kwargs):
    kwargs['parse_float'] = Decimal
    super().__init__(*args, **kwargs)
  # class JSONLatain
