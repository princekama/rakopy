"""Data models for rakopy module."""

from dataclasses import dataclass
from typing import List

@dataclass
class HubStatus:
    """Hub status data model."""
    product_type: str
    protocol_version: int
    id: str
    mac_address: str
    version: str

@dataclass
class Channel:
    """Channel data model."""
    id: int
    title: str
    type: str
    color_type: str
    color_title: str
    multi_channel_component: str

@dataclass
class Scene:
    """Scene data model."""
    id: int
    title: int

@dataclass
class Room:
    """Room data model."""
    id: int
    title: str
    type: str
    mode: str
    channels: List[Channel]
    scenes: List[Scene]

@dataclass
class LevelInfo:
    """Channel level info data model."""
    kelvin: int
    red: int
    green: int
    blue: int

@dataclass
class ChannelLevel:
    """Channel level data model."""
    channel_id: int
    current_level: int
    target_level: int
    level_info: LevelInfo

@dataclass
class Level:
    """Level data model."""
    room_id: int
    current_scene_id: int
    channel_levels: List[ChannelLevel]

@dataclass
class LevelChangedEvent:
    """Level changed event data model."""
    room_id: int
    channel_id: int
    current_level: int
    target_level: int
    time_to_take: int
    temporary: bool

@dataclass
class SceneChangedEvent:
    """Scene changed event data model."""
    room_id: int
    channel_id: int
    scene_id: int
    active_scene_id: int
