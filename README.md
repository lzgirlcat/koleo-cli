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
 - check seat allocation statistics( authentication <u>is</u> required since may 2026 :< )
 - check delays(after login)

### login
  - the current implementation allows you to store the credentials as cleartext, or instruct the koleo-cli to execute a command to retrieve them
  - the builtin login function allows you to store the data using secret-tool on linux, or cleartext on other platforms
  - you can create your own auth provider using the `command` auth type:
    - the program has to output a json k: v dump of cookies to be used, including the `_koleo_token` cookie(the v2 bearer auth token)

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
usage: koleo [-h] [-c CONFIG] [--ignore_cache] [--nocolor]
             {departures,d,dep,odjazdy,o,arrivals,a,arr,przyjazdy,p,all,w,wszystkie,all_trains,pociagi,trainroute,r,tr,t,poc,pociąg,traincalendar,kursowanie,tc,k,traindetail,td,tid,id,idpoc,stations,s,find,f,stacje,ls,q,connections,z,szukaj,path,destinations,do,to,z3,trainstats,ts,tp,miejsca,frekwencja,trainconnectionstats,tcs,aliases,clear_cache,login} ...

Koleo CLI

options:
  -h, --help            show this help message and exit
  -c, --config CONFIG   Custom config path.
  --ignore_cache
  --nocolor             Disable color output and formatting

actions:
  {departures,d,dep,odjazdy,o,arrivals,a,arr,przyjazdy,p,all,w,wszystkie,all_trains,pociagi,trainroute,r,tr,t,poc,pociąg,traincalendar,kursowanie,tc,k,traindetail,td,tid,id,idpoc,stations,s,find,f,stacje,ls,q,connections,z,szukaj,path,destinations,do,to,z3,trainstats,ts,tp,miejsca,frekwencja,trainconnectionstats,tcs,aliases,clear_cache,login}
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
    connections (z, szukaj, path)
                        Allows you to search for connections from a to b
    destination_connections (destinations, do, to)
                        Allows you to search for connections from favourite_station to x
    v3_connections (z3)
                        Allows you to search for connections from a to b using V3 Koleo Search
    trainstats (ts, tp, miejsca, frekwencja)
                        Allows you to check seat allocation info for a train.
    trainconnectionstats (tcs)
                        Allows you to check the seat allocations on the train connection given it's koleo ID
    aliases             Save quick aliases for station names!
    clear_cache         Allows you to clear koleo-cli cache
    login               Allows you to login(this is required for trainstats:<)
```

## Example Config
```json
{
  "cache": {},
  "favourite_station": "czarna-bialostocka",
  "disable_cache": false,
  "use_roman_numerals": false,
  "aliases": {
    "bzw": "bialystok-zielone-wzgorza",
    "b": "bialystok",
    "s": "sokolka",
    "su": "suwalki",
    "bp": "bielsk-podlaski",
    "ww": "warszawa-wschodnia",
    "e": "elk",
    "og": "olsztyn-glowny",
    "kg": "krakow-glowny",
    "k": "katowice",
    "bb": "bialystok-bacieczki",
    "wg": "warszawa-gdanska",
    "wz": "warszawa-zachodnia",
    "wc": "warszawa-centralna",
    "bbg": "bielsko-biala-glowna",
    "cb": "czarna-bialostocka",
    "bdg": "bydgoszcz-glowna",
    "sg": "szczecin-glowny"
  },
  "show_connection_id": false,
  "use_country_flags_emoji": true,
  "use_station_type_emoji": true,
  "platform_first": false,
  "auto_głównx": true,
  "show_seconds": false,
  "auth": {
    "type": "command",
    "data": [
      "secret-tool",
      "lookup",
      "service",
      "koleo-cli",
      "account",
      "default"
    ],
    "on_update": [
      "secret-tool",
      "store",
      "--label='Koleo-CLI Auth'",
      "service",
      "koleo-cli",
      "account",
      "default"
    ]
  }
}
```