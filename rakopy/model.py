"""Data models for rakopy module"""

from dataclasses import dataclass


@dataclass
class HubInfo:
    """Hub information data model"""
    protocol_version: int
    hub_id: str
    mac_address: str
    hub_version: str

@dataclass
class Room:
    """Room data model"""
    room_id: int
    room_title: str
    room_type: str
    room_mode: str

@dataclass
class Channel:
    """Channel data model"""
    room_id: int
    room_title: str
    room_type: str
    room_mode: str
    channel_id: int
    channel_title: str
    channel_type: str
    scenes_level: dict

@dataclass
class Level:
    """Room and channel level data model"""
    room_id: int
    channel_id: int
    current_scene: int
    current_level: int
    target_level: int

@dataclass
class Scene:
    """Scene data model"""
    room_id: int
    scene_id: int
    scene_title: int

@dataclass
class Colour:
    """Room and channel colour data model"""
    room_id: int
    room_title: str
    channel_id: int
    channel_title: str
    type: str

@dataclass
class ColourLevel:
    """Room and channel colour level data model"""
    room_id: int
    channel_id: int
    type: str
    level: int
    red_or_kelvin: int
    green: int
    blue: int
