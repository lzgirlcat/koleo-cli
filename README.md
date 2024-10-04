[![PyPI - Version](https://img.shields.io/pypi/v/koleo-cli.svg)](https://pypi.org/project/koleo-cli)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/koleo-cli.svg)](https://pypi.org/project/koleo-cli)

# Koleo CLI

![gif showcasing the functionality](https://github.com/lzgirlcat/koleo-cli/blob/main/koleo-cli.gif?raw=true)


install via pip by running

`pip install koleo-cli`

## it currently allows you to:
 - get departures/arrival list for a station
 - get train info given its number and name(pull requests are welcome if you know how to get a train object by just the number)
 - find a station or list all known stations
 - find a connection from station a to b, with filtering by operators
 - save a station as your favourite to quickly check it's departures

additionally you can also use the KoleoAPI wrapper directly in your own projects, all returns are fully typed using `typing.TypedDict`

## MY(possibly controversial) design choices:
 - platforms and track numbers are shown using arabic numerals instead of roman
   - you can change it by adding `use_roman_numerals: true` to your config.json file
 - most api queries are cached for 24h
   - you can change it by adding `disable_cache: true` to your config.json file
 - the cli.py code is really dirty but printing formatted data is hard :<

pull requests are welcome!!

```
usage: koleo [-h] [-c CONFIG] [--nocolor] {departures,d,dep,odjazdy,o,arrivals,a,arr,przyjazdy,p,trainroute,r,tr,t,poc,pociąg,stations,s,find,f,stacje,ls,connections,do,z,szukaj,path} ...

Koleo CLI

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Custom config path.
  --nocolor             Disable color output and formatting

actions:
  {departures,d,dep,odjazdy,o,arrivals,a,arr,przyjazdy,p,trainroute,r,tr,t,poc,pociąg,stations,s,find,f,stacje,ls,connections,do,z,szukaj,path}
    departures (d, dep, odjazdy, o)
                        Allows you to list station departures
    arrivals (a, arr, przyjazdy, p)
                        Allows you to list station departures
    trainroute (r, tr, t, poc, pociąg)
                        Allows you to show the train's route
    stations (s, find, f, stacje, ls)
                        Allows you to find stations by their name
    connections (do, z, szukaj, path)
                        Allows you to search for connections from a to b
```