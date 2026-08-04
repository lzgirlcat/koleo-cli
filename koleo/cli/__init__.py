from .auth import UserManagement
from .aliases import Aliases
from .connections import Connections
from .seats import Seats
from .station_board import StationBoard
from .stations import Stations
from .tickets import Tickets


class CLI(UserManagement, Tickets, Aliases, StationBoard, Connections, Seats, Stations): ...
