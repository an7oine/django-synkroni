# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
  setup_requires='git-versiointi',
  name='django-synkroni',
  description='Django/Javascript-synkronointirajapinta',
  url='https://github.com/an7oine/django-synkroni.git',
  author='Antti Hautaniemi',
  author_email='antti.hautaniemi@me.com',
  licence='MIT',
  packages=find_packages(),
  include_package_data=True,
  zip_safe=False,
  install_requires=[
    'django>=3.1',
    'django-pistoke',
  ],
  entry_points={
    'django.sovellus': ['synkroni = synkroni.Synkroni'],
  }
)
