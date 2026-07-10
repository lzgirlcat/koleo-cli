from .auth import UserManagement
from .aliases import Aliases
from .connections import Connections
from .seats import Seats
from .station_board import StationBoard
from .stations import Stations


class CLI(UserManagement, Aliases, StationBoard, Connections, Seats, Stations): ...
