from .aliases import Aliases
from .connections import Connections
from .seats import Seats
from .station_board import StationBoard
from .stations import Stations
from .train_info import TrainInfo


class CLI(Aliases, StationBoard, Connections, Seats, Stations): ...
