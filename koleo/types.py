import typing as t


class BaseStationInfo(t.TypedDict):
    id: int
    name: str
    name_slug: str


# i want to kms
class ExtendedBaseStationInfo(BaseStationInfo):
    hits: int
    version: str  # "A", "B"
    is_group: bool
    city: str | None
    region: str
    country: str
    latitude: float
    longitued: float


class ExtendedStationInfo(BaseStationInfo):
    ibnr: int
    localised_name: str
    on_demand: bool


class StationBannerClockHandsPositon(t.TypedDict):
    x: float
    y: float


class StationBannerClockHands(t.TypedDict):
    url: str | None
    position: StationBannerClockHandsPositon


class StationBannerClock(t.TypedDict):
    visible: bool | None
    hands: StationBannerClockHands


class StationBanner(t.TypedDict):
    url: str
    clock: StationBannerClock


class Address(t.TypedDict):
    full: str
    zip: str


class Feature(t.TypedDict):
    id: str
    name: str
    available: bool


class StationOpeningHours(t.TypedDict):
    day: int  # 0-6
    open: str  # 00:00
    close: str  # 24:00


class StationDetails(t.TypedDict):
    banner: StationBanner
    address: Address
    lat: float
    lon: float
    opening_hours: list[StationOpeningHours]
    features: list[Feature]


class StationLocalizedToTrain(BaseStationInfo):
    train_id: int


class ApiBrand(t.TypedDict):
    id: int
    name: str  # EIC, IC, IR, REG, ...
    display_name: str
    logo_text: str
    color: str  # hex
    carrier_id: int


class Carrier(t.TypedDict):
    id: int
    name: str  # Koleje Dolnośląskie, POLREGIO
    short_name: str  # KD, PR
    slug: str
    legal_name: str  # PKP Szybka Kolej Miejska w Trójmieście Sp.z o.o.


class DiscountInfo(t.TypedDict):
    id: int
    passenger_percentage: int
    display_passenger_percentage: float
    flyer_second_class_percentage: int
    flyer_first_class_percentage: int
    express_second_class_percentage: int
    express_first_class_percentage: int
    dependent_on_ids: list[int]
    name: str
    rank: int
    season_passenger_percentage: int
    displayable: bool
    is_company: bool


class TrainOnStationInfo(t.TypedDict):
    arrival: str | None  # first station
    departure: str | None  # last station
    stations: list[StationLocalizedToTrain]
    train_full_name: str
    brand_id: int
    platform: str  # could be empty; some countries dont use arabic numerals or even tracks
    track: str  # could be empty; some countries dont use arabic numerals or even tracks


class TrainCalendar(t.TypedDict):
    id: int
    train_nr: int
    train_name: str
    trainBrand: int
    dates: list[str]  # Y-M-D
    train_ids: list[int]
    date_train_map: dict[str, int]


class TrainCalendarResponse(t.TypedDict):
    train_calendars: list[TrainCalendar]


class TimeDict(t.TypedDict):
    hour: int
    minute: int
    second: int


TrainAttribute = t.Tuple[int, str, str, str, bool, str]


class TrainDetail(t.TypedDict):
    id: int
    train_nr: int
    name: str | None
    train_full_name: str
    run_desc: str  # "09.09-15.09 - w pt - nd; 16.09-29.09, 14.10-03.11 - codziennie; 30.09-06.10 - w pn; 07.10-13.10 - we wt - nd; 04.11-10.11 - w pn - sb"
    carrier_id: int
    brand_id: int
    train_name: int  # wtf
    duration_offset: int  # wtf?
    db_train_nr: int  # lol


class TrainStop(t.TypedDict):
    id: int
    station_id: int
    station_name: str
    station_slug: str
    train_id: int
    arrival: TimeDict
    departure: TimeDict
    position: int  # the stop nr
    train_nr: int | None
    brand_id: int
    distance: int  # meters
    entry_only: bool
    exit_only: bool
    station_display_name: str
    platform: str
    vehicle_type: str | None  # ED161


class TrainDetailResponse(t.TypedDict):
    train: TrainDetail
    stops: list[TrainStop]


class ConnectionTrainStop(t.TypedDict):
    arrival: TimeDict | str  # WTF KOLEO!!!!
    departure: TimeDict | str  # WTF KOLEO!!!!
    distance: int
    in_path: bool
    station_id: int
    next_day: bool
    position: int
    train_nr: int
    brand_id: int
    entry_only: bool
    exit_only: bool
    platform: str
    track: str
    on_demand: bool


class ConnectiontrainDetail(TrainDetail):
    arrival: TimeDict | str  # WTF KOLEO!!!!
    departure: TimeDict | str  # WTF KOLEO!!!!
    stops: list[ConnectionTrainStop]
    bookable: bool
    train_attribute_ids: list[int]
    travel_time: int
    direction: str
    start_station_id: int
    end_station_id: int
    fixed_carriage_composition: bool
    is_option_groups_available: bool


class ErrorDict(t.TypedDict):
    type: str
    value: str


class ConnectionDetail(t.TypedDict):
    id: int
    distance: int
    purchasable: bool
    purchasable_errors: list[ErrorDict]
    travel_time: int
    changes: int
    needs_document: bool
    brand_ids: list[int]
    start_station_id: int
    end_station_id: int
    arrival: TimeDict | str  # WTF KOLEO!!!!
    departure: TimeDict | str  # WTF KOLEO!!!!
    bookable: bool
    special_event_slug: str | None
    is_advanced_travel_options: bool
    is_child_birthday_required: bool
    max_passengers_count: bool
    constriction_info: list[str]
    is_estimated_timetable_available: bool
    trains: list[ConnectiontrainDetail]
