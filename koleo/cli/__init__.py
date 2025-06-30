from .aliases import Aliases
from .station_board import StationBoard
from .connections import Connections
from .train_info import TrainInfo
from .seats import Seats
from .stations import Stations


class CLI(Aliases, StationBoard, Connections, Seats, Stations): ...
