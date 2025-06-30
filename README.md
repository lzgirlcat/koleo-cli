# Koleo CLI
[![PyPI - Version](https://img.shields.io/pypi/v/koleo-cli.svg)](https://pypi.org/project/koleo-cli)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/koleo-cli.svg)](https://pypi.org/project/koleo-cli)

## Installation
**install via pip by running** `pip install koleo-cli`


![gif showcasing the functionality](https://github.com/lzgirlcat/koleo-cli/blob/main/koleo-cli.gif?raw=true)

## it currently allows you to:
 - get departures/arrival list for a station
 - get train info given its number and name(pull requests are welcome if you know how to get a train object by just the number)
 - find a station or list all known stations
 - find a connection from station a to b, with filtering by operators
 - save a station as your favourite to quickly check it's departures
 - add station aliases to query them more easily
 - check seat allocation statistics

### coming soon™️:
 - TUI ticket purchase interface
 - ticket display
 - your previous tickets + stats
 - find empty compartments 
additionally you can also use the KoleoAPI wrapper directly in your own projects, all returns are fully typed using `typing.TypedDict`

## MY(possibly controversial) design choices:
 - platforms and track numbers are shown using arabic numerals instead of roman
   - you can change it by adding `use_roman_numerals: true` to your `koleo-cli.json` config file
 - most api queries are cached for 24h
   - you can change it by adding `disable_cache: true` to your `koleo-cli.json` config file
 - stations/ls uses emojis by default
   - you can disable them by adding `use_country_flags_emoji: false` and `use_country_flags_emoji: false` to your `koleo-cli.json` config file
pull requests are welcome!!

```
usage: koleo [-h] [-c CONFIG] [--nocolor]
             {departures,d,dep,odjazdy,o,arrivals,a,arr,przyjazdy,p,all,w,wszystkie,all_trains,pociagi,trainroute,r,tr,t,poc,pociąg,traincalendar,kursowanie,tc,k,traindetail,td,tid,id,idpoc,stations,s,find,f,stacje,ls,q,connections,do,z,szukaj,path,trainstats,ts,tp,miejsca,frekwencja,trainconnectionstats,tcs,aliases} ...

Koleo CLI

options:
  -h, --help            show this help message and exit
  -c, --config CONFIG   Custom config path.
  --nocolor             Disable color output and formatting

actions:
  {departures,d,dep,odjazdy,o,arrivals,a,arr,przyjazdy,p,all,w,wszystkie,all_trains,pociagi,trainroute,r,tr,t,poc,pociąg,traincalendar,kursowanie,tc,k,traindetail,td,tid,id,idpoc,stations,s,find,f,stacje,ls,q,connections,do,z,szukaj,path,trainstats,ts,tp,miejsca,frekwencja,trainconnectionstats,tcs,aliases}
    departures (d, dep, odjazdy, o)
                        Allows you to list station departures
    arrivals (a, arr, przyjazdy, p)
                        Allows you to list station departures
    all (w, wszystkie, all_trains, pociagi)
                        Allows you to list all station trains
    trainroute (r, tr, t, poc, pociąg)
                        Allows you to check the train's route
    traincalendar (kursowanie, tc, k)
                        Allows you to check what days the train runs on
    traindetail (td, tid, id, idpoc)
                        Allows you to show the train's route given it's koleo ID
    stations (s, find, f, stacje, ls, q)
                        Allows you to find stations by their name
    connections (do, z, szukaj, path)
                        Allows you to search for connections from a to b
    trainstats (ts, tp, miejsca, frekwencja)
                        Allows you to check seat allocation info for a train.
    trainconnectionstats (tcs)
                        Allows you to check the seat allocations on the train connection given it's koleo ID
    aliases             Save quick aliases for station names!
```