"""Tests for rakopy.hub.Hub."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, call

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from rakopy.hub import Hub
from rakopy.consts import DEFAULT_PORT
from rakopy.errors import ConfigValidationError, SendCommandError
from rakopy.model import (
    Channel, ChannelLevel, HubStatus, Level,
    LevelChangedEvent, LevelInfo, Room, Scene, SceneChangedEvent,
)
from tests.conftest import make_reader, make_writer, json_line


# ---------------------------------------------------------------------------
# Hub.__init__ validation
# ---------------------------------------------------------------------------
class TestHubInit:
    def test_valid_init(self):
        hub = Hub("client", "192.168.1.1")
        assert hub.host == "192.168.1.1"
        assert hub.port == DEFAULT_PORT
        assert hub.client_name == "client"

    def test_custom_port(self):
        hub = Hub("client", "192.168.1.1", port=1234)
        assert hub.port == 1234

    def test_host_stripped(self):
        hub = Hub("client", "  192.168.1.1  ")
        assert hub.host == "192.168.1.1"

    def test_empty_host_raises(self):
        with pytest.raises(ConfigValidationError, match="host"):
            Hub("client", "")

    def test_whitespace_host_raises(self):
        with pytest.raises(ConfigValidationError, match="host"):
            Hub("client", "   ")

    def test_empty_client_name_raises(self):
        with pytest.raises(ConfigValidationError, match="client_name"):
            Hub("", "192.168.1.1")

    def test_negative_port_raises(self):
        with pytest.raises(ConfigValidationError, match="port"):
            Hub("client", "192.168.1.1", port=-1)

    def test_port_too_high_raises(self):
        with pytest.raises(ConfigValidationError, match="port"):
            Hub("client", "192.168.1.1", port=65536)

    def test_port_boundary_zero(self):
        hub = Hub("client", "192.168.1.1", port=0)
        assert hub.port == 0

    def test_port_boundary_max(self):
        hub = Hub("client", "192.168.1.1", port=65535)
        assert hub.port == 65535


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _patch_connection(hub, reader_responses):
    """Patch a hub so _reconnect is a no-op and reader/writer are mocked."""
    hub._writer = make_writer()
    hub._reader = make_reader(reader_responses)


def _sub_ack():
    """SUB acknowledgement line returned on connect."""
    return json_line({"name": "sub", "payload": {}})


def _send_ok():
    """Successful send response."""
    return json_line({"name": "send", "payload": {"result": 1}})


def _send_error(msg="UNKNOWN_ERROR"):
    """Error send response."""
    return json_line({"name": "error", "payload": {"message": msg}})


# ---------------------------------------------------------------------------
# Hub._build_send_request (static)
# ---------------------------------------------------------------------------
class TestBuildSendRequest:
    def test_scene_command(self):
        req = Hub._build_send_request(1, 2, {"command": "scene", "scene": 3})
        assert req == {
            "name": "send",
            "payload": {
                "room": 1,
                "channel": 2,
                "action": {"command": "scene", "scene": 3},
            },
        }

    def test_level_command(self):
        req = Hub._build_send_request(1, 2, {"command": "levelrate", "level": 255})
        assert req["payload"]["action"]["command"] == "levelrate"
        assert req["payload"]["action"]["level"] == 255

    def test_fade_up(self):
        req = Hub._build_send_request(1, 0, {"command": "fade", "down": False})
        assert req["payload"]["action"]["down"] is False

    def test_fade_down(self):
        req = Hub._build_send_request(1, 0, {"command": "fade", "down": True})
        assert req["payload"]["action"]["down"] is True

    def test_stop(self):
        req = Hub._build_send_request(1, 0, {"command": "stop"})
        assert req["payload"]["action"]["command"] == "stop"

    def test_store(self):
        req = Hub._build_send_request(1, 2, {"command": "store", "scene": 1})
        assert req["payload"]["action"]["command"] == "store"


# ---------------------------------------------------------------------------
# Hub._to_room (static)
# ---------------------------------------------------------------------------
class TestToRoom:
    def test_basic_room(self):
        data = {
            "roomId": 17,
            "title": "Master Bedroom",
            "type": "LIGHT",
            "mode": "S4OFF",
            "channel": [
                {
                    "channelId": 1,
                    "title": "Ceiling",
                    "type": "SLIDER",
                    "colorType": "RGB",
                    "colorTitle": "Ceiling",
                    "multiChannelComponent": None,
                },
            ],
            "scene": [
                {"sceneId": 1, "title": "Casual"},
                {"sceneId": 2, "title": "Formal"},
            ],
        }
        room = Hub._to_room(data)
        assert room.id == 17
        assert room.title == "Master Bedroom"
        assert room.type == "LIGHT"
        assert room.mode == "S4OFF"
        assert len(room.channels) == 1
        # Scene 0 (Off) is always prepended
        assert len(room.scenes) == 3
        assert room.scenes[0] == Scene(id=0, title="Off")
        assert room.scenes[1] == Scene(id=1, title="Casual")

    def test_room_without_mode(self):
        data = {
            "roomId": 9,
            "title": "Test room",
            "type": "LIGHT",
            "channel": [],
            "scene": [],
        }
        room = Hub._to_room(data)
        assert room.mode is None

    def test_multi_channel_rgb_inherits_from_first(self):
        """Channels without colorType should inherit from the first channel."""
        data = {
            "roomId": 40,
            "title": "E+F",
            "type": "LIGHT",
            "mode": "SNAMEDOFF",
            "channel": [
                {
                    "channelId": 8,
                    "title": "Red Wall",
                    "type": "SLIDER",
                    "colorType": "RGB",
                    "colorTitle": "Wall",
                    "multiChannelComponent": "RED",
                },
                {
                    "channelId": 9,
                    "title": "Green Wall",
                    "type": "SLIDER",
                },
                {
                    "channelId": 10,
                    "title": "Blue Wall",
                    "type": "SLIDER",
                },
            ],
            "scene": [],
        }
        room = Hub._to_room(data)
        assert room.channels[0].color_type == "RGB"
        assert room.channels[0].multi_channel_component == "RED"
        # Channels 2 and 3 inherit color_type from channel 1
        assert room.channels[1].color_type == "RGB"
        assert room.channels[2].color_type == "RGB"
        # They also inherit color_title
        assert room.channels[1].color_title == "Wall"
        assert room.channels[2].color_title == "Wall"

    def test_off_scene_always_first(self):
        data = {
            "roomId": 1,
            "title": "Room",
            "type": "LIGHT",
            "channel": [],
            "scene": [{"sceneId": 1, "title": "Scene 1"}],
        }
        room = Hub._to_room(data)
        assert room.scenes[0].id == 0
        assert room.scenes[0].title == "Off"

    def test_empty_channels_and_scenes(self):
        data = {
            "roomId": 5,
            "title": "Empty",
            "type": "SWITCH",
            "channel": [],
            "scene": [],
        }
        room = Hub._to_room(data)
        assert room.channels == []
        assert len(room.scenes) == 1  # only the Off scene


# ---------------------------------------------------------------------------
# Hub._to_level (static)
# ---------------------------------------------------------------------------
class TestToLevel:
    def test_level_with_level_info(self):
        data = {
            "roomId": 45,
            "currentScene": 1,
            "channel": [
                {
                    "channelId": 1,
                    "currentLevel": 50,
                    "targetLevel": 50,
                    "levelInfo": {"kelvin": 2700, "red": 0, "green": 0, "blue": 0},
                },
            ],
        }
        level = Hub._to_level(data)
        assert level.room_id == 45
        assert level.current_scene_id == 1
        assert len(level.channel_levels) == 1
        assert level.channel_levels[0].level_info.kelvin == 2700

    def test_level_without_level_info(self):
        data = {
            "roomId": 45,
            "currentScene": -1,
            "channel": [
                {
                    "channelId": 0,
                    "currentLevel": 127,
                    "targetLevel": 127,
                    "levelInfo": None,
                },
            ],
        }
        level = Hub._to_level(data)
        assert level.channel_levels[0].level_info is None

    def test_multiple_channels(self):
        data = {
            "roomId": 10,
            "currentScene": 2,
            "channel": [
                {"channelId": 0, "currentLevel": 0, "targetLevel": 0, "levelInfo": None},
                {
                    "channelId": 1,
                    "currentLevel": 200,
                    "targetLevel": 200,
                    "levelInfo": {"kelvin": 0, "red": 255, "green": 128, "blue": 64},
                },
            ],
        }
        level = Hub._to_level(data)
        assert len(level.channel_levels) == 2
        assert level.channel_levels[1].current_level == 200
        assert level.channel_levels[1].level_info.red == 255


# ---------------------------------------------------------------------------
# Hub._reconnect
# ---------------------------------------------------------------------------
class TestReconnect:
    @pytest.mark.asyncio
    async def test_reconnect_opens_connection(self):
        hub = Hub("test_client", "192.168.1.42")
        sub_response = _sub_ack()

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_conn:
            reader = make_reader([sub_response])
            writer = make_writer()
            mock_conn.return_value = (reader, writer)

            await hub._reconnect()

            mock_conn.assert_called_once_with("192.168.1.42", DEFAULT_PORT)
            # Should have sent SUB message
            writer.write.assert_called_once()
            sent = writer.write.call_args[0][0].decode()
            assert "SUB,JSON," in sent
            assert '"client_name": "test_client"' in sent
            assert '"subscriptions": []' in sent

    @pytest.mark.asyncio
    async def test_reconnect_skips_if_connected(self):
        hub = Hub("test_client", "192.168.1.42")
        hub._writer = make_writer()
        hub._reader = make_reader([])

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_conn:
            await hub._reconnect()
            mock_conn.assert_not_called()

    @pytest.mark.asyncio
    async def test_reconnect_if_transport_closing(self):
        hub = Hub("test_client", "192.168.1.42")
        hub._writer = make_writer()
        hub._writer.transport.is_closing.return_value = True

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_conn:
            reader = make_reader([_sub_ack()])
            writer = make_writer()
            mock_conn.return_value = (reader, writer)

            await hub._reconnect()
            mock_conn.assert_called_once()


# ---------------------------------------------------------------------------
# Hub.get_hub_status
# ---------------------------------------------------------------------------
class TestGetHubStatus:
    @pytest.mark.asyncio
    async def test_get_hub_status(self):
        hub = Hub("test_client", "192.168.1.42")
        response = json_line({
            "name": "status",
            "payload": {
                "productType": "Hub",
                "protocolVersion": 2,
                "hubId": "ebbe7961-7abb-3aed-9fef-0bb7871ef74d",
                "mac;": "70:B3:D5:08:43:27",
                "hubVersion": "3.1.5",
            },
        })

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [response])
            status = await hub.get_hub_status()

        assert isinstance(status, HubStatus)
        assert status.product_type == "Hub"
        assert status.protocol_version == 2
        assert status.id == "ebbe7961-7abb-3aed-9fef-0bb7871ef74d"
        assert status.mac_address == "70:B3:D5:08:43:27"
        assert status.version == "3.1.5"

    @pytest.mark.asyncio
    async def test_get_hub_status_sends_correct_request(self):
        hub = Hub("test_client", "192.168.1.42")
        response = json_line({
            "name": "status",
            "payload": {
                "productType": "Hub",
                "protocolVersion": 2,
                "hubId": "id",
                "mac;": "mac",
                "hubVersion": "1.0",
            },
        })

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [response])
            await hub.get_hub_status()

        sent_data = json.loads(hub._writer.write.call_args[0][0].decode().strip())
        assert sent_data == {"name": "status", "payload": {}}


# ---------------------------------------------------------------------------
# Hub.get_rooms
# ---------------------------------------------------------------------------
class TestGetRooms:
    @pytest.mark.asyncio
    async def test_get_all_rooms(self):
        hub = Hub("test_client", "192.168.1.42")
        payload = [
            {
                "roomId": 9,
                "title": "Test room",
                "type": "LIGHT",
                "mode": "S4OFF",
                "channel": [
                    {
                        "channelId": 1,
                        "title": "Ceiling",
                        "type": "SLIDER",
                        "colorType": None,
                        "colorTitle": None,
                        "multiChannelComponent": None,
                    }
                ],
                "scene": [{"sceneId": 1, "title": "Casual"}],
            },
            {
                "roomId": 10,
                "title": "Kitchen",
                "type": "LIGHT",
                "channel": [],
                "scene": [],
            },
        ]
        response = json_line({"name": "query_SCENECHANNEL", "payload": payload})

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [response])
            rooms = await hub.get_rooms()

        assert len(rooms) == 2
        assert rooms[0].id == 9
        assert rooms[0].title == "Test room"
        assert rooms[1].id == 10

    @pytest.mark.asyncio
    async def test_get_rooms_sends_scenechannel_query(self):
        hub = Hub("test_client", "192.168.1.42")
        response = json_line({"name": "query_SCENECHANNEL", "payload": []})

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [response])
            await hub.get_rooms()

        sent_data = json.loads(hub._writer.write.call_args[0][0].decode().strip())
        assert sent_data["name"] == "query"
        assert sent_data["payload"]["queryType"] == "SCENECHANNEL"
        assert sent_data["payload"]["roomId"] == 0

    @pytest.mark.asyncio
    async def test_get_rooms_by_id(self):
        hub = Hub("test_client", "192.168.1.42")
        payload = [
            {
                "roomId": 17,
                "title": "Bedroom",
                "type": "LIGHT",
                "mode": None,
                "channel": [],
                "scene": [],
            }
        ]
        response = json_line({"name": "query_SCENECHANNEL", "payload": payload})

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [response])
            rooms = await hub.get_rooms(room_id=17)

        sent_data = json.loads(hub._writer.write.call_args[0][0].decode().strip())
        assert sent_data["payload"]["roomId"] == 17
        assert len(rooms) == 1
        assert rooms[0].id == 17


# ---------------------------------------------------------------------------
# Hub.get_levels
# ---------------------------------------------------------------------------
class TestGetLevels:
    @pytest.mark.asyncio
    async def test_get_all_levels(self):
        hub = Hub("test_client", "192.168.1.42")
        payload = [
            {
                "roomId": 45,
                "currentScene": -1,
                "channel": [
                    {
                        "channelId": 0,
                        "currentLevel": 50,
                        "targetLevel": 50,
                        "levelInfo": None,
                    },
                    {
                        "channelId": 1,
                        "currentLevel": 50,
                        "targetLevel": 50,
                        "levelInfo": {"kelvin": 2700, "red": 0, "green": 0, "blue": 0},
                    },
                ],
            }
        ]
        response = json_line({"name": "query_LEVEL", "payload": payload})

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [response])
            levels = await hub.get_levels()

        assert len(levels) == 1
        assert levels[0].room_id == 45
        assert len(levels[0].channel_levels) == 2
        assert levels[0].channel_levels[1].level_info.kelvin == 2700

    @pytest.mark.asyncio
    async def test_get_levels_sends_level_query(self):
        hub = Hub("test_client", "192.168.1.42")
        response = json_line({"name": "query_LEVEL", "payload": []})

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [response])
            await hub.get_levels()

        sent_data = json.loads(hub._writer.write.call_args[0][0].decode().strip())
        assert sent_data["payload"]["queryType"] == "LEVEL"
        assert sent_data["payload"]["roomId"] == 0

    @pytest.mark.asyncio
    async def test_get_levels_by_room(self):
        hub = Hub("test_client", "192.168.1.42")
        response = json_line({"name": "query_LEVEL", "payload": []})

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [response])
            await hub.get_levels(room_id=17)

        sent_data = json.loads(hub._writer.write.call_args[0][0].decode().strip())
        assert sent_data["payload"]["roomId"] == 17


# ---------------------------------------------------------------------------
# Hub.set_level
# ---------------------------------------------------------------------------
class TestSetLevel:
    @pytest.mark.asyncio
    async def test_set_level(self):
        hub = Hub("test_client", "192.168.1.42")

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [_send_ok()])
            await hub.set_level(room_id=1, channel_id=2, level=255)

        sent_data = json.loads(hub._writer.write.call_args[0][0].decode().strip())
        assert sent_data == {
            "name": "send",
            "payload": {
                "room": 1,
                "channel": 2,
                "action": {"command": "levelrate", "level": 255},
            },
        }

    @pytest.mark.asyncio
    async def test_set_level_zero(self):
        hub = Hub("test_client", "192.168.1.42")

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [_send_ok()])
            await hub.set_level(room_id=1, channel_id=0, level=0)

        sent_data = json.loads(hub._writer.write.call_args[0][0].decode().strip())
        assert sent_data["payload"]["action"]["level"] == 0


# ---------------------------------------------------------------------------
# Hub.set_scene
# ---------------------------------------------------------------------------
class TestSetScene:
    @pytest.mark.asyncio
    async def test_set_scene(self):
        hub = Hub("test_client", "192.168.1.42")

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [_send_ok()])
            await hub.set_scene(room_id=1, channel_id=2, scene=3)

        sent_data = json.loads(hub._writer.write.call_args[0][0].decode().strip())
        assert sent_data == {
            "name": "send",
            "payload": {
                "room": 1,
                "channel": 2,
                "action": {"command": "scene", "scene": 3},
            },
        }

    @pytest.mark.asyncio
    async def test_set_scene_off(self):
        hub = Hub("test_client", "192.168.1.42")

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [_send_ok()])
            await hub.set_scene(room_id=1, channel_id=0, scene=0)

        sent_data = json.loads(hub._writer.write.call_args[0][0].decode().strip())
        assert sent_data["payload"]["action"]["scene"] == 0


# ---------------------------------------------------------------------------
# Hub.set_rgb
# ---------------------------------------------------------------------------
class TestSetRgb:
    @pytest.mark.asyncio
    async def test_set_rgb_default(self):
        hub = Hub("test_client", "192.168.1.42")

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [_send_ok()])
            await hub.set_rgb(room_id=16, channel_id=2, red=25, green=50, blue=255)

        sent_data = json.loads(hub._writer.write.call_args[0][0].decode().strip())
        assert sent_data == {
            "name": "send-color",
            "payload": {
                "room": 16,
                "channel": 2,
                "colorSendType": "SEND_COLOR_AND_LEVEL",
                "red": 25,
                "green": 50,
                "blue": 255,
                "rgbExcludesBrightness": False,
                "level": None,
            },
        }

    @pytest.mark.asyncio
    async def test_set_rgb_color_only(self):
        """When rgbExcludesBrightness=True and no level, use SEND_COLOR_ONLY."""
        hub = Hub("test_client", "192.168.1.42")

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [_send_ok()])
            await hub.set_rgb(
                room_id=16, channel_id=2,
                red=255, green=0, blue=128,
                rgb_excludes_brightness=True,
            )

        sent_data = json.loads(hub._writer.write.call_args[0][0].decode().strip())
        assert sent_data["payload"]["colorSendType"] == "SEND_COLOR_ONLY"
        assert sent_data["payload"]["rgbExcludesBrightness"] is True

    @pytest.mark.asyncio
    async def test_set_rgb_with_level(self):
        """When rgbExcludesBrightness=True but level is set, use SEND_COLOR_AND_LEVEL."""
        hub = Hub("test_client", "192.168.1.42")

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [_send_ok()])
            await hub.set_rgb(
                room_id=16, channel_id=2,
                red=255, green=0, blue=128,
                rgb_excludes_brightness=True,
                level=200,
            )

        sent_data = json.loads(hub._writer.write.call_args[0][0].decode().strip())
        assert sent_data["payload"]["colorSendType"] == "SEND_COLOR_AND_LEVEL"
        assert sent_data["payload"]["level"] == 200


# ---------------------------------------------------------------------------
# Hub.set_temperature
# ---------------------------------------------------------------------------
class TestSetTemperature:
    @pytest.mark.asyncio
    async def test_set_temperature_color_only(self):
        hub = Hub("test_client", "192.168.1.42")

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [_send_ok()])
            await hub.set_temperature(room_id=16, channel_id=2, temperature=2700)

        sent_data = json.loads(hub._writer.write.call_args[0][0].decode().strip())
        assert sent_data == {
            "name": "send-colorTemp",
            "payload": {
                "room": 16,
                "channel": 2,
                "colorSendType": "SEND_COLOR_ONLY",
                "temperature": 2700,
                "level": None,
            },
        }

    @pytest.mark.asyncio
    async def test_set_temperature_with_level(self):
        hub = Hub("test_client", "192.168.1.42")

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [_send_ok()])
            await hub.set_temperature(
                room_id=16, channel_id=2, temperature=2700, level=200
            )

        sent_data = json.loads(hub._writer.write.call_args[0][0].decode().strip())
        assert sent_data["payload"]["colorSendType"] == "SEND_COLOR_AND_LEVEL"
        assert sent_data["payload"]["level"] == 200
        assert sent_data["payload"]["temperature"] == 2700


# ---------------------------------------------------------------------------
# Hub.start_fading_up / start_fading_down / stop_fading
# ---------------------------------------------------------------------------
class TestFading:
    @pytest.mark.asyncio
    async def test_start_fading_up(self):
        hub = Hub("test_client", "192.168.1.42")

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [_send_ok()])
            await hub.start_fading_up(room_id=1, channel_id=0)

        sent_data = json.loads(hub._writer.write.call_args[0][0].decode().strip())
        assert sent_data["payload"]["action"] == {"command": "fade", "down": False}

    @pytest.mark.asyncio
    async def test_start_fading_down(self):
        hub = Hub("test_client", "192.168.1.42")

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [_send_ok()])
            await hub.start_fading_down(room_id=1, channel_id=0)

        sent_data = json.loads(hub._writer.write.call_args[0][0].decode().strip())
        assert sent_data["payload"]["action"] == {"command": "fade", "down": True}

    @pytest.mark.asyncio
    async def test_stop_fading(self):
        hub = Hub("test_client", "192.168.1.42")

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [_send_ok()])
            await hub.stop_fading(room_id=1, channel_id=0)

        sent_data = json.loads(hub._writer.write.call_args[0][0].decode().strip())
        assert sent_data["payload"]["action"] == {"command": "stop"}


# ---------------------------------------------------------------------------
# Hub.store_scene
# ---------------------------------------------------------------------------
class TestStoreScene:
    @pytest.mark.asyncio
    async def test_store_scene(self):
        hub = Hub("test_client", "192.168.1.42")

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [_send_ok()])
            await hub.store_scene(room_id=1, channel_id=2, scene=1)

        sent_data = json.loads(hub._writer.write.call_args[0][0].decode().strip())
        assert sent_data == {
            "name": "send",
            "payload": {
                "room": 1,
                "channel": 2,
                "action": {"command": "store", "scene": 1},
            },
        }


# ---------------------------------------------------------------------------
# Hub._send error handling
# ---------------------------------------------------------------------------
class TestSendErrorHandling:
    @pytest.mark.asyncio
    async def test_send_raises_on_error_response(self):
        hub = Hub("test_client", "192.168.1.42")

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [_send_error("UNKNOWN_ERROR")])
            with pytest.raises(SendCommandError):
                await hub.set_level(room_id=1, channel_id=2, level=255)

    @pytest.mark.asyncio
    async def test_send_succeeds_on_ok_response(self):
        hub = Hub("test_client", "192.168.1.42")

        with patch.object(hub, "_reconnect", new_callable=AsyncMock):
            _patch_connection(hub, [_send_ok()])
            # Should not raise
            await hub.set_level(room_id=1, channel_id=2, level=100)


# ---------------------------------------------------------------------------
# Hub.get_events
# ---------------------------------------------------------------------------
class TestGetEvents:
    @pytest.mark.asyncio
    async def test_scene_event(self):
        hub = Hub("test_client", "192.168.1.42")

        scene_tracker = json_line({
            "name": "tracker",
            "type": "scene",
            "payload": {
                "roomId": 85,
                "channelId": 0,
                "scene": 4,
                "activeScene": 4,
            },
        })

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_conn:
            reader = make_reader([scene_tracker])
            writer = make_writer()
            mock_conn.return_value = (reader, writer)

            events = []
            async for event in hub.get_events():
                events.append(event)
                break  # only consume one event

        assert len(events) == 1
        assert isinstance(events[0], SceneChangedEvent)
        assert events[0].room_id == 85
        assert events[0].channel_id == 0
        assert events[0].scene_id == 4
        assert events[0].active_scene_id == 4

    @pytest.mark.asyncio
    async def test_level_event(self):
        hub = Hub("test_client", "192.168.1.42")

        level_tracker = json_line({
            "name": "tracker",
            "type": "level",
            "payload": {
                "roomId": 85,
                "channelId": 4,
                "currentLevel": 127,
                "targetLevel": 90,
                "timeToTake": 230,
                "temporary": False,
            },
        })

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_conn:
            reader = make_reader([level_tracker])
            writer = make_writer()
            mock_conn.return_value = (reader, writer)

            events = []
            async for event in hub.get_events():
                events.append(event)
                break

        assert len(events) == 1
        assert isinstance(events[0], LevelChangedEvent)
        assert events[0].room_id == 85
        assert events[0].channel_id == 4
        assert events[0].current_level == 127
        assert events[0].target_level == 90
        assert events[0].time_to_take == 230
        assert events[0].temporary is False

    @pytest.mark.asyncio
    async def test_event_subscription_sends_tracker_sub(self):
        hub = Hub("test_client", "192.168.1.42")

        level_tracker = json_line({
            "name": "tracker",
            "type": "level",
            "payload": {
                "roomId": 1,
                "channelId": 1,
                "currentLevel": 0,
                "targetLevel": 0,
                "timeToTake": 0,
                "temporary": False,
            },
        })

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_conn:
            reader = make_reader([level_tracker])
            writer = make_writer()
            mock_conn.return_value = (reader, writer)

            async for _ in hub.get_events():
                break

        sent = writer.write.call_args[0][0].decode()
        assert "SUB,JSON," in sent
        assert '"subscriptions": ["TRACKER"]' in sent

    @pytest.mark.asyncio
    async def test_multiple_events(self):
        hub = Hub("test_client", "192.168.1.42")

        events_data = [
            json_line({
                "name": "tracker",
                "type": "scene",
                "payload": {
                    "roomId": 1, "channelId": 0, "scene": 1, "activeScene": 1,
                },
            }),
            json_line({
                "name": "tracker",
                "type": "level",
                "payload": {
                    "roomId": 1, "channelId": 1,
                    "currentLevel": 100, "targetLevel": 200,
                    "timeToTake": 500, "temporary": False,
                },
            }),
        ]

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_conn:
            reader = make_reader(events_data)
            writer = make_writer()
            mock_conn.return_value = (reader, writer)

            collected = []
            async for event in hub.get_events():
                collected.append(event)
                if len(collected) >= 2:
                    break

        assert isinstance(collected[0], SceneChangedEvent)
        assert isinstance(collected[1], LevelChangedEvent)

    @pytest.mark.asyncio
    async def test_non_tracker_events_ignored(self):
        hub = Hub("test_client", "192.168.1.42")

        events_data = [
            json_line({
                "name": "feedback",
                "payload": {"room": 1, "channel": 1},
            }),
            json_line({
                "name": "tracker",
                "type": "scene",
                "payload": {
                    "roomId": 1, "channelId": 0, "scene": 2, "activeScene": 2,
                },
            }),
        ]

        with patch("asyncio.open_connection", new_callable=AsyncMock) as mock_conn:
            reader = make_reader(events_data)
            writer = make_writer()
            mock_conn.return_value = (reader, writer)

            collected = []
            async for event in hub.get_events():
                collected.append(event)
                break

        # The feedback event should be skipped, only the scene tracker yielded
        assert len(collected) == 1
        assert isinstance(collected[0], SceneChangedEvent)
        assert collected[0].scene_id == 2
