from dataclasses import dataclass


@dataclass
class HubInfo:
    protocol_version: int
    hub_id: str
    mac_address: str
    hub_version: str

@dataclass
class Room:
    room_id: int
    room_tile: str
    room_type: str
    room_mode: str

@dataclass
class Channel:
    room_id: int
    room_tile: str
    room_type: str
    room_mode: str
    channel_id: int
    channel_title: str
    channel_type: str
    scene1: int
    scene2: int
    scene3: int
    scene4: int
    scene5: int
    scene6: int
    scene7: int
    scene8: int
    scene9: int
    scene10: int
    scene11: int
    scene12: int
    scene13: int
    scene14: int
    scene15: int
    scene16: int

@dataclass
class Level:
    room_id: int
    channel_id: int
    current_scene: int
    current_level: int
    target_level: int

@dataclass
class Scene:
    room_id: int
    scene_id: int
    scene_title: int

@dataclass
class Colour:
    room_id: int
    room_title: str
    channel_id: int
    channel_title: str
    type: str

@dataclass
class ColourLevel:
    room_id: int
    channel_id: int
    type: str
    level: int
    red_or_kelvin: int
    green: int
    blue: int
