"""Tests for rakopy.model dataclasses."""
# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=too-few-public-methods,duplicate-code

from rakopy.model import (
    Channel,
    ChannelLevel,
    HubStatus,
    Level,
    LevelChangedEvent,
    LevelInfo,
    Room,
    Scene,
    SceneChangedEvent,
)


class TestHubStatus:
    def test_creation(self):
        status = HubStatus(
            product_type="Hub",
            protocol_version=2,
            id="ebbe7961-7abb-3aed-9fef-0bb7871ef74d",
            mac_address="70:B3:D5:08:40:00",
            version="3.1.5",
        )
        assert status.product_type == "Hub"
        assert status.protocol_version == 2
        assert status.id == "ebbe7961-7abb-3aed-9fef-0bb7871ef74d"
        assert status.mac_address == "70:B3:D5:08:40:00"
        assert status.version == "3.1.5"

    def test_equality(self):
        a = HubStatus("Hub", 2, "id1", "mac1", "3.0.0")
        b = HubStatus("Hub", 2, "id1", "mac1", "3.0.0")
        assert a == b

    def test_inequality(self):
        a = HubStatus("Hub", 2, "id1", "mac1", "3.0.0")
        b = HubStatus("Hub", 2, "id2", "mac1", "3.0.0")
        assert a != b


class TestChannel:
    def test_creation(self):
        ch = Channel(
            id=1,
            title="Ceiling",
            type="SLIDER",
            color_type="RGB",
            color_title="Ceiling",
            multi_channel_component=None,
        )
        assert ch.id == 1
        assert ch.title == "Ceiling"
        assert ch.type == "SLIDER"
        assert ch.color_type == "RGB"
        assert ch.color_title == "Ceiling"
        assert ch.multi_channel_component is None

    def test_multi_channel_component(self):
        ch = Channel(
            id=8,
            title="Red Wall",
            type="SLIDER",
            color_type="RGB",
            color_title="Wall",
            multi_channel_component="RED",
        )
        assert ch.multi_channel_component == "RED"


class TestScene:
    def test_creation(self):
        scene = Scene(id=1, title="Casual")
        assert scene.id == 1
        assert scene.title == "Casual"

    def test_off_scene(self):
        scene = Scene(id=0, title="Off")
        assert scene.id == 0
        assert scene.title == "Off"


class TestRoom:
    def test_creation(self):
        room = Room(
            id=17,
            title="Master Bedroom",
            type="LIGHT",
            mode="S4OFF",
            channels=[Channel(1, "Ceiling", "SLIDER", None, None, None)],
            scenes=[Scene(0, "Off"), Scene(1, "Casual")],
        )
        assert room.id == 17
        assert room.title == "Master Bedroom"
        assert room.type == "LIGHT"
        assert room.mode == "S4OFF"
        assert len(room.channels) == 1
        assert len(room.scenes) == 2

    def test_room_types(self):
        """Verify all documented room types can be used."""
        for room_type in ["LIGHT", "BLIND", "SWITCH", "CURTAIN",
                          "BLIND_SMART", "CURTAIN_SMART", "VENTILATION"]:
            room = Room(id=1, title="Test", type=room_type, mode=None,
                        channels=[], scenes=[])
            assert room.type == room_type


class TestLevelInfo:
    def test_kelvin_only(self):
        info = LevelInfo(kelvin=2700, red=0, green=0, blue=0)
        assert info.kelvin == 2700

    def test_rgb_only(self):
        info = LevelInfo(kelvin=0, red=255, green=128, blue=64)
        assert info.red == 255
        assert info.green == 128
        assert info.blue == 64


class TestChannelLevel:
    def test_with_level_info(self):
        info = LevelInfo(kelvin=2700, red=0, green=0, blue=0)
        cl = ChannelLevel(channel_id=1, current_level=50, target_level=50, level_info=info)
        assert cl.channel_id == 1
        assert cl.current_level == 50
        assert cl.target_level == 50
        assert cl.level_info.kelvin == 2700

    def test_without_level_info(self):
        cl = ChannelLevel(channel_id=0, current_level=127, target_level=127, level_info=None)
        assert cl.level_info is None


class TestLevel:
    def test_creation(self):
        level = Level(
            room_id=45,
            current_scene_id=-1,
            channel_levels=[
                ChannelLevel(0, 50, 50, None),
                ChannelLevel(1, 50, 50, LevelInfo(2700, 0, 0, 0)),
            ],
        )
        assert level.room_id == 45
        assert level.current_scene_id == -1
        assert len(level.channel_levels) == 2


class TestLevelChangedEvent:
    def test_creation(self):
        event = LevelChangedEvent(
            room_id=85,
            channel_id=4,
            current_level=127,
            target_level=90,
            time_to_take=230,
            temporary=False,
        )
        assert event.room_id == 85
        assert event.channel_id == 4
        assert event.current_level == 127
        assert event.target_level == 90
        assert event.time_to_take == 230
        assert event.temporary is False

    def test_temporary_event(self):
        event = LevelChangedEvent(85, 4, 127, 90, 230, True)
        assert event.temporary is True


class TestSceneChangedEvent:
    def test_creation(self):
        event = SceneChangedEvent(
            room_id=85,
            channel_id=0,
            scene_id=4,
            active_scene_id=4,
        )
        assert event.room_id == 85
        assert event.channel_id == 0
        assert event.scene_id == 4
        assert event.active_scene_id == 4
