import typing as t


class BaseStationInfo(t.TypedDict):
    id: int
    name: str
    name_slug: str


StationType = t.Literal["TopographicalPlace", "Quay", "StopPlace", "railStopPlace", "busStopPlace", "group"]
TransportMode = t.Literal[
    "bus",
    "rail",
]


# i want to kms
class ExtendedStationInfo(BaseStationInfo):
    latitude: float
    longitude: float
    hits: int
    ibnr: int
    city: str | None
    region: str
    country: str
    localised_name: str
    is_group: bool
    has_announcements: bool
    is_nearby_station_enabled: bool
    is_livesearch_displayable: bool
    type: StationType
    transport_mode: TransportMode | None
    time_zone: str  # Europe/Warsaw


class SearchStationInfo(BaseStationInfo):
    ibnr: int
    localised_name: str
    on_demand: bool
    type: StationType


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


class Brand(t.TypedDict):
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
    supports_mobywatel_from: str | None


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
    trainBrand: int  # why is this snakecase? wth
    dates: list[str]  # Y-M-D
    train_ids: list[int]
    date_train_map: dict[str, int]


class TrainCalendarResponse(t.TypedDict):
    train_calendars: list[TrainCalendar]


class TimeDict(t.TypedDict):
    hour: int
    minute: int
    second: int


TrainAttributeTuple = t.Tuple[int, str, str, str, bool, str]
# id, name, start_station, end_station, no idea, style?( <- "icon-warning"?)


class TrainDetail(t.TypedDict):
    id: int
    train_nr: int
    name: str | None
    train_full_name: str
    run_desc: str  # "09.09-15.09 - w pt - nd; 16.09-29.09, 14.10-03.11 - codziennie;"
    carrier_id: int
    brand_id: int
    train_name: int  # wtf
    duration_offset: int  # wtf?
    db_train_nr: int  # lol
    train_attributes: list[TrainAttributeTuple]


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


# 410 GONE :<
# class TrainDetailResponse(t.TypedDict):
#     train: TrainDetail
#     stops: list[TrainStop]


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


class ConnectionTrainDetail(TrainDetail):
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
    train_id: int  # wtf!!!!!!!!!!!


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
    trains: list[ConnectionTrainDetail]
    eol_connection_uuid: str | None


class SpecialCompartmentType(t.TypedDict):
    id: int
    icon: str
    name: str
    information: str
    terms: str


SeatState = t.Literal["FREE", "RESERVED", "BLOCKED"]


class Seat(t.TypedDict):
    carriage_nr: str  # number
    seat_nr: str  # number
    special_compartment_type_id: int
    state: SeatState
    placement_id: int  # 1 -> okno, 2 -> korytarz, 7 -> środek


class SeatsAvailabilityResponse(t.TypedDict):
    special_compartment_types: list[SpecialCompartmentType]
    seats: list[Seat]


class Price(t.TypedDict):
    id: int
    connection_id: int
    value: str
    tariff_ids: list[int]
    tariff_names: list[str]
    validity: str
    area_extract: ...
    document_required: bool
    valid_hours: float
    changes_allowed: bool
    bike_price: str | None
    luggage_price: str | None
    dog_price: str | None
    bike_available: bool
    dog_available: bool
    luggage_available: bool
    two_way: bool
    warning: str | None
    is_bike: bool
    main_ticket_nr_required: bool
    allows_zero_price: bool
    is_seat_booking: bool
    is_booking_after_purchase_available: bool
    is_two_way: bool
    has_pr_tariff: bool
    tariff_descriptions: list[str]
    discount_percentage: int
    uncertain_to: bool
    dividable: bool
    limited_bike_price: str | None
    has_ic_tariff: bool
    has_valid_anticommunist_passengers: bool
    has_valid_baby_passengers: bool
    is_luggage_plus_available: bool
    kdr_bike_price_available: bool
    available_return_days: list[str]


class Placement(t.TypedDict):
    id: int
    name: str
    key: str


class CompartmentType(t.TypedDict):
    id: int
    rank: int | None
    name: str
    selected: bool
    terms: str
    information: str
    placement_selection_for_each_passenger_possible: bool
    placements: list[Placement]


class ReservatioModePreference(t.TypedDict):
    available: bool
    compartment_types: list[CompartmentType]


class ResevervationMode(t.TypedDict):
    seat_map: bool
    place_indication: bool
    adjacent_place_indication: bool
    preferences: ReservatioModePreference


class PlaceType(t.TypedDict):
    id: int | None
    icon: str
    place_types_label: str
    name: str
    price: float
    base_price: float
    unavailable_help_text: str
    available: bool
    selected: bool
    uncertain: bool
    capacity: int
    place_types: "list[PlaceType]"


class TrainPlaceType(t.TypedDict):
    id: int
    train_nr: int
    place_type: PlaceType


class NestedTrainPlaceTypesResponse(t.TypedDict):
    train_place_types: list[TrainPlaceType]


class CurrentSession(t.TypedDict):
    id: t.Literal["current"]
    email: str


class TrainCompositonCarriage(t.TypedDict):
    positon: int
    number: str  # lol
    carriage_type_id: int
    bookable: bool
    is_default: bool


Direction = t.Literal["right", "left"]


class SimpleTrainDirection(t.TypedDict):
    type: t.Literal["simple"]
    direction: Direction
    reversingOnRoute: bool


class TrainComposition(t.TypedDict):
    direction: SimpleTrainDirection
    carriages: list[TrainCompositonCarriage]


class CarriageSeat(t.TypedDict):
    nr: int
    seat_type_id: int
    x: int
    y: int
    color: str | None
    compartment_type_id: (
        int | None
    )  # not implemented by koleo, returns 1: "wagon bezprzedziałowy" for "wagon przedziałowy"
    placement_id: int | None


class CarriageSeatType(t.TypedDict):
    id: int
    key: str
    width: int
    height: int


class CarriageType(t.TypedDict):
    id: int
    key: str
    image_key: str
    seats: list[CarriageSeat]
    seat_types: list[CarriageSeatType]


class Passenger(t.TypedDict):
    id: int
    first_name: str
    last_name: str
    discount_id: int
    discount_card_ids: list[int]
    birthday: str
    fellow: bool
    is_selected: bool
    avatar_url: str | None
    active: bool
    identity_document_type_id: int | None
    identity_document_number: str | None
    company_code: str | None
    has_big_discount: bool


class User(t.TypedDict):
    email: str
    locale: Placement
    passenger_id: int
    consent_to_terms: bool
    consent_to_privacy: bool
    consent_to_trade_info: bool | None
    constriction_notifications: bool
    wallet_id: int
    lka_wallet_id: int
    money_back: bool
    masscollect_account_number: str | None
    affiliate_code: str | None
    application_installed: bool
    has_exchange_order: bool | None
    should_use_new_travel_options: bool


class Wallet(t.TypedDict):
    id: int
    balance: int  # 8.75 -> 875
    last_transaction: str | None


class CurrentUser(t.TypedDict):
    passengers: list[Passenger]
    users: list[User]
    wallets: list[Wallet]
    lka_wallets: list[Wallet]


class StationKeyword(t.TypedDict):
    id: int
    keyword: str
    station_id: int


class TrainAttribute(t.TypedDict):
    id: int
    name: str
    short_name: str
    rank: int
    warning: bool


class AttributeWithAnnotation(t.TypedDict):
    attribute_definition_id: int
    annotation: str


class V3LegStop(t.TypedDict):
    station_id: int
    arrival: str
    departure: str
    commercial_brand_id: int
    internal_brand_id: int
    train_nr: int
    platform: str
    track: str
    for_alighting: bool
    for_boarding: bool
    request_stop: bool


V3LegType = t.Literal["train_leg", "station_change_leg", "walk_leg"]


class V3BaseConnectionLeg(t.TypedDict):
    leg_type: V3LegType
    duration: int  # minutes


class V3BaseTravelLeg(V3BaseConnectionLeg):
    origin_station_id: int
    destination_station_id: int
    departure: str  # iso with tz
    arrival: str


class BasicTrainLeg(V3BaseTravelLeg):
    leg_type: t.Literal["train_leg"]
    train_nr: int
    train_name: str
    train_full_name: str
    departure_platform: str  # roman
    departure_track: str  # arabic
    arrival_platform: str
    arrival_track: str


class V3TrainLeg(BasicTrainLeg):
    leg_type: t.Literal["train_leg"]
    train_id: int
    operating_day: str  # YYYY-MM-DD
    commercial_brand_id: int
    internal_brand_id: int
    constrictions: list[AttributeWithAnnotation]
    stops_before_leg: list[V3LegStop]
    stops_in_leg: list[V3LegStop]
    stops_after_leg: list[V3LegStop]
    attributes: list[AttributeWithAnnotation]


class V3StationChangeLeg(V3BaseTravelLeg):
    leg_type: t.Literal["station_change_leg"]
    station_id: int


class V3WalkLeg(V3BaseTravelLeg):
    leg_type: t.Literal["walk_leg"]
    footpath_duration: int


V3ConnectionLeg = t.Union[V3StationChangeLeg, V3WalkLeg, V3TrainLeg]


class V3ConnectionResult(t.TypedDict):
    uuid: str
    eol_response_version: int
    departure: str  # datetime iso
    arrival: str  # datetime iso
    origin_station_id: int
    destination_station_id: int
    duration: int  # minutes
    changes: int
    constrictions: list[AttributeWithAnnotation]
    legs: list[V3ConnectionLeg]


class V3PricePerPassenger(t.TypedDict):
    value: str  # zł.gr
    passenger_id: int | None


class V3Price(t.TypedDict):
    price: str  # zł.gr
    uncertain: bool
    price_label: str | None
    is_child_birthday_required: bool
    needs_document: bool
    purchasable: bool
    purchasable_errors: list[ErrorDict]
    price_per_passengers: list[V3PricePerPassenger]
    additional_info: str


class CarrierLine(t.TypedDict):
    start_station_name: str
    start_station_slug: str
    end_station_name: str
    end_station_slug: str


CallType = t.Literal["recorded"]


class EstimatedTrainTime(t.TypedDict):
    call_type: CallType
    aimed_arrival: str | None
    aimed_departure: str | None
    actual_arrival: str | None
    actual_departure: str | None
    train_id: int
    operating_day: str  # yyyy-mm-dd
    recorded_at: str | None


class EstimatedTrainLeg(t.TypedDict):
    train_id: int
    origin_station_id: int
    destination_station_id: int
    origin_call: str | None
    destination_call: str | None


class EstimatedV3ConnectionTimesResponse(t.TypedDict):
    train_legs: list[EstimatedTrainLeg]


class LoginTokenResponse(t.TypedDict):
    access_token: str
    token_type: t.Literal["Bearer"]
    expires_in: int  # 1209600 -> 336h -> 14 dni
    refresh_token: str
    created_at: int


class RealtimeTrainStop(t.TypedDict):
    station_id: int
    arrival: str
    departure: str
    commercial_brand_id: int
    internal_brand_id: int
    train_nr: int
    platform: str  # roman numeral
    track: str  # arabic numeral
    request_stop: bool
    for_alighting: bool
    for_boarding: bool
    expected_arrival: str | None
    expected_departure: str | None
    actual_arrival: str | None
    actual_departure: str | None


class TrainTimetable(t.TypedDict):
    train_id: int
    train_nr: int
    train_name: str
    train_full_name: str
    operating_day: str  # yyyy-mm-dd
    commercial_brand_id: int
    internal_brand_id: int
    constrictions: list[AttributeWithAnnotation]
    train_attributes: list[AttributeWithAnnotation]
    real_time_data_recorded_at: str | None
    stops: list[RealtimeTrainStop]


class ReservationDataPlace(t.TypedDict):
    seat_nr: str
    type: str


class ReservationData(t.TypedDict):
    carriage_nr: str
    compartment_type_name: str
    place_type_category_key: str
    places: list[ReservationDataPlace]
    seat_class: t.Literal[1, 2]


class ReservationDataWithTrain(t.TypedDict):
    train_nr: str
    reservations_data: list[ReservationData]


class TicketOwnerData(t.TypedDict):
    ticket_ids: list[int]
    first_name: str
    last_name: str
    avatar_url: str  # empty if null!?


class OrderStatusInfo(t.TypedDict):
    title: str  # np. twój bilet został zwrócony
    additional_info: str
    tickets_displayable: bool
    status_displayable: bool


class OrderTrainLegReservation(t.TypedDict):
    place_type_category_key: t.Literal["", "seat_1"]
    carriage_nr: str
    compartment_type_name: str  # wagon przedziałowy, etc
    travel_class: str
    place_numbers: str  # split by \u2013 – for some reason???
    place_placements: str  # okno, "Okno i Okno (xd)" etc


class OrderTrainLeg(BasicTrainLeg):
    train_icon: t.Literal["generic-train"]
    train_brand_id: int
    origin_station_name: str
    train_final_station_name: str
    destination_station_name: str
    no_reservation_message: str | None
    reservations: list[OrderTrainLegReservation]
    extras: list[TicketExtra]


OrderStatus = t.Literal["finished", "refunded", "created", "paid", "exchanged", "being_refunded", "being_exchanged"]

OrderTravelSummaryLegTypes = OrderTrainLeg | V3WalkLeg | V3StationChangeLeg


class OrderTravelSummary(t.TypedDict):
    legs: list[OrderTravelSummaryLegTypes]


class Order(t.TypedDict):
    id: int
    start_station_id: int
    end_station_id: int
    start_datetime: str  # ISO
    end_datetime: str  # ISO
    can_be_returned: bool
    brand_ids: list[int]
    changes: int
    price: str  # 2137.69
    returnable_price: str  # 420.67
    status: OrderStatus
    connection_id: int
    payment_id: int
    is_season: bool
    is_zonal: bool
    is_network: bool
    seats_reservations: list  # unknown
    reservation_data: list[ReservationDataWithTrain]
    name: str  # start_station - end_station, Czarna Białostocka - Książki
    valid_from: str  # ISO
    valid_to: str  # ISO
    is_renewable: bool
    is_return_booking_available: bool
    is_travel_plan_available: bool
    can_be_exchanged: bool
    ticket_owners: list[TicketOwnerData]
    refund_info: str
    is_refund_amount_unknown: bool
    has_invoices: bool
    can_create_invoice: bool
    is_name_change_available: bool
    travel_summary: OrderTravelSummary
    luggage_plus_id: int | None
    status_info: OrderStatusInfo
    uuid: str
    requires_start_time: bool
    should_search_for_return_connection: bool
    refund_deadline: str  # ISO
    exchange_deadline: str  # ISO
    name_change_deadline: str | None  # ISO


class PaginatedOrdersResponse(t.TypedDict):
    current_page: int
    per_page: int
    total_results: int
    orders: list[Order]


class PTU(t.TypedDict):
    type: t.Literal["B"]
    value: str  # 0.21
    rate: str  # 8%


class TicketSection(t.TypedDict):
    relation: str  # a - b
    barnd: str
    brand_short: str
    train_class: str  # 2


class TicketIssuer(t.TypedDict):
    name: str
    nip: str


class TicketPassengerDataInfo(t.TypedDict):
    passengers_count: int
    passengers_info: str
    discount_code: str


class TicketExtra(t.TypedDict):
    type: t.Literal["dogs", "bike", "luggage"]
    value: int  # amount?
    name: str
    price: str


class TicketIdentityVerification(t.TypedDict):
    first_name: str
    last_name: str
    image: str  # base64
    verified_discount: int | None  # probably...


class Ticket(t.TypedDict):
    id: int
    price: str
    total_price: str
    distance: int  # 0 for some wtf?
    tariff_name: str
    discount_id: int
    offer_info: str
    normal_passengers_count: int
    normal_passengers_info: str
    discounted_passengers_info: str
    discounted_passengers_count: int
    discount_code: str
    valid_from: str  # ISO
    valid_to: str  # ISO
    ptu: list[PTU]
    purchase_date: str  # ISO
    emergency_code: str | None
    extras: list[TicketExtra]
    owner_name: str
    owner_document_number: str | None
    owner_document_type_id: str | None
    serial_number: str
    verification_token: str | None
    base64_img: str
    start_station_id: int
    end_station_id: int
    sections: list[TicketSection]
    carrier_id: int
    carrier_name: str
    train_class: t.Literal[1, 2]
    start_datetime: str  # ISO
    end_datetime: str  # ISO
    via_info: str
    is_network: bool
    is_season: bool
    is_return: bool
    is_zonal: bool
    extract: str  # Bilet ważny 20 minut od 15:18.\nWażny na obszarze aglomeracji Łódzkiej, ograniczonym stacjami: Zgierz Kontrewers, Pabianice, Łódź Andrzejóww.
    bike_info: str | None  # can be null
    seats_info: str | None
    bus_info: str | None
    document_notice: bool
    company_codes: str
    full_extract: str
    basic_extract: bool
    issuer: TicketIssuer
    discount_ids: list[int]
    normal_passengers_data_info: TicketPassengerDataInfo
    discounted_passengers_data_info: list[TicketPassengerDataInfo]
    discounts_extract: str
    identity_verifications: list[TicketIdentityVerification]


class FullOrder(Order):
    tickets: list[Ticket]
    payment_method: str
    is_wallet_pass_available: bool


class YearlySummary(t.TypedDict):
    year: int
    token: str


class V2User(t.TypedDict):
    agreed_to_terms: bool
    privacy_accepted: bool
    email: str
    name: str
    surname: str
    document_number: str | None
    document_type_id: str | None
    birthday: str | None
    discount_id: int
    discount_card_ids: list[int]
    affiliate_code: str
    koleo_wallet_balance: str  # zł.gr
    masscollect_account_number: str | None
    confirmed: bool
    is_selected: bool
    company_code: str | None
    passenger_id: int
    money_back: bool
    locale: str
    consent_to_trade_info: bool | None
    constriction_notifications: bool
    user_yearly_summaries: list[YearlySummary]
    is_mobywatel_verified: bool


class MobywatelState(t.TypedDict):
    is_ticket_verification_on: bool
    user_photo: str  # base64
    verified_discounts: list
    discounts_to_verify: list


class V2UserWithMobywatel(V2User):
    is_mobywatel_verified: t.Literal[True]
    mobywatel_state: MobywatelState


class GoogleWalletTokenResponse(t.TypedDict):
    jwt: str


class MobywatelVerificationCodeResponse(t.TypedDict):
    qr_code: str
    code: str
    code_deadline: str
    environment: t.Literal["production"]  # TODO: there may be more


class MobywatelVerificationStatusResponseBase(t.TypedDict):
    status: t.Literal["success", "not_started"]
    error_messages: list  # TODO: check type
    last_attempt_at: str | None  # not sure, but it prolly will be null if the user has never started the auth process


class MobywatelVerificationSuccessStatus(MobywatelVerificationStatusResponseBase):
    status: t.Literal["success"]  # TODO: there may be more
    error_messages: list  # TODO: check type
    last_attempt_at: str | None  # not sure, but it prolly will be null if the user has never started the auth process
    message: str


MobywatelVerificationStatus = MobywatelVerificationStatusResponseBase | MobywatelVerificationSuccessStatus
