from __future__ import annotations

import asyncio
from typing import List
from consts import DEFAULT_PORT
from errors import SendCommandError
from model import Channel, Colour, ColourLevel, HubInfo, Level, Room, Scene


class RakoHub:
    def __init__(
        self,
        client_name: str,
        host: str,
        port: int = DEFAULT_PORT
    ):
        host = host.strip()
        if not host:
            raise Exception("RakoHub: host parameter cannot be empty")
        
        if port < 0 or port > 65535:
            raise Exception("RakoHub: port should be between 0 and 65535")
        
        client_name = client_name.strip()
        if not client_name:
            raise Exception("RakoHub: client_name parameter cannot be empty")
        
        if "," in client_name:
            raise Exception("RakoHub: invalid character ',' in client_name")
        
        self.host = host
        self.port = port
        self.client_name = client_name
        
        self._reader = None
        self._writer = None

    async def get_channels(self, room_id: int = None) -> List[Channel]:
        """
        Get list of channels in a room. If room is not specified, returns all channels.
        """
        return await self._query("CHANNEL", self._to_channel, room_id)
    
    async def get_colours(self, room_id: int = None) -> List[Colour]:
        """
        Get list colour enabled channels in a room. 
        If room is not specified, returns colour enabled channels for all the rooms.
        """
        return await self._query("COLOR", self._to_colour, room_id)
    
    async def get_colours_levels(self, room_id: int = None) -> List[ColourLevel]:
        """
        Get list of brightness levels for all the channels in a room. 
        If room is not specified, returns brightness levels for all the rooms and channels.
        """
        return await self._query("COLOR_LEVEL", self._to_colour_level, room_id)
    
    async def get_hub_info(self) -> HubInfo:
        """
        Get Rako Hub information.
        """
        await self._reconnect()
        
        request = "STATUS,0\r\n"

        self._writer.write(str.encode(request))
        await self._writer.drain()
        
        response = (await self._reader.readline()).decode().split(",")

        hubInfo = HubInfo(
            protocol_version= response[2], 
            hub_id= response[3], 
            mac_address= response[4], 
            hub_version= response[5]
        )
        
        return hubInfo

    async def get_levels(self, room_id: int = None) -> List[Level]:
        """
        Get list of brightness levels for all the channels in a room. 
        If room is not specified, returns brightness levels for all the rooms and channels.
        """
        return await self._query("LEVEL", self._to_level, room_id)
    
    async def get_rooms(self, room_id: int = None) -> List[Room]:
        """
        Get room by its id. If room_id is not specified, returns all the rooms.
        """
        return await self._query("ROOM", self._to_room, room_id)
    
    async def get_scenes(self, room_id: int = None) -> List[Scene]:
        """
        Get list of scenes for a room. 
        If room is not specified, returns scenes for all the rooms.
        """
        return await self._query("SCENE", self._to_scene, room_id)
    
    async def set_level(self, room_id: int, channel_id: int, level: int) -> None:
        """
        Set level for a given room and channel
        """
        await self._send("LEVEL", room_id, channel_id, [level])

    async def set_rgb(self, room_id: int, channel_id: int, red: int, green: int, blue: int) -> None:
        """
        Set RGB for a given room and channel
        """
        await self._send("RGB", room_id, channel_id, [red, green, blue])

    async def set_scene(self, room_id: int, channel_id: int, scene: int) -> None:
        """
        Set a scene for a given room and channel
        """
        await self._send("SCENE", room_id, channel_id, [scene])

    async def set_kelvin(self, room_id: int, channel_id: int, temperature: int) -> None:
        """
        Set a colour temperature for a given room and channel
        """
        await self._send("KELVIN", room_id, channel_id, [temperature])

    async def start_fading_down(self, room_id: int, channel_id: int) -> None:
        """
        Start fading down brightness for a given room and channel
        """
        await self._send("FADE_DOWN", room_id, channel_id, [1])

    async def start_fading_up(self, room_id: int, channel_id: int) -> None:
        """
        Start fading up brightness for a given room and channel
        """
        await self._send("FADE_UP", room_id, channel_id, [1])

    async def stop_fading(self, room_id: int, channel_id: int) -> None:
        """
        Stop fading brightness for a given room and channel
        """
        await self._send("FADE_STOP", room_id, channel_id, [1])

    async def store_scene(self, room_id: int, channel_id: int, scene: int) -> None:
        """
        Store current levels as a scene for a given room and channel
        """
        await self._send("STORE", room_id, channel_id, [scene])

    async def _query(self, query: str, func, room_id: int = None):
        """
        Executes query and returns result
        """
        await self._reconnect()
        
        if room_id is None:
            request = "QUERY,{0}\r\n".format(query)
        else:
            request = "QUERY,{0},{1}\r\n".format(query, room_id)

        self._writer.write(str.encode(request))
        await self._writer.drain()
        
        result = []
        while True:
            data = (await self._reader.readline()).decode().split(",")
            if data[0] == "QUERY_HEADER":
                continue
            if data[0] == "QUERY_COMPLETE":
                break
            result.append(func(data))
        
        return result

    async def _reconnect(self) -> None:
        """
        Try to reconnect to the Rako Hub if the connection was not previously established or was closed.
        """
        if (self._writer is None or 
            self._writer.transport is None or 
            self._writer.transport.is_closing()
        ):
            self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
        
            request = "SUB,BASIC,V4,{0}\r\n".format(self.client_name)
            
            self._writer.write(str.encode(request))
            await self._writer.drain()
            
            await self._reader.readline()

    async def _send(self, command: str, room_id: int, channel_id: int, values: List[int]) -> None:
        """
        Sends a command
        """
        await self._reconnect()

        request = "SEND,{0},{1},{2},".format(room_id, channel_id, command)
        for val in values:
            request += str(val)

        request += "\r\n"
        
        self._writer.write(str.encode(request))
        await self._writer.drain()
        
        response = (await self._reader.readline()).decode().split(",")
        if response[0] == "AERROR":
            raise SendCommandError(
                "Failed to send {0} command to room {1} and channel {2}".format(
                    command, 
                    room_id, 
                    channel_id
                )
            )

    @staticmethod
    def _to_channel(data: List[str]) -> Channel:
        """
        Converts list of str to Channel.
        """
        return Channel(
                    room_id= data[1],
                    room_tile= data[2],
                    room_type= data[3],
                    room_mode= data[4],
                    channel_id= data[5],
                    channel_title= data[6],
                    channel_type= data[7],
                    scene1= data[8],
                    scene2= data[9],
                    scene3= data[10],
                    scene4= data[11],
                    scene5= data[12],
                    scene6= data[13],
                    scene7= data[14],
                    scene8= data[15],
                    scene9= data[16],
                    scene10= data[17],
                    scene11= data[18],
                    scene12= data[19],
                    scene13= data[20],
                    scene14= data[21],
                    scene15= data[22],
                    scene16= data[23].rstrip()
                )

    @staticmethod
    def _to_colour(data: List[str]) -> Colour:
        """
        Converts list of str to Colour.
        """
        return Colour(
                    room_id= data[1],
                    room_title= data[2],
                    channel_id= data[3],
                    channel_title= data[4],
                    type= data[5].rstrip()
                )

    @staticmethod
    def _to_colour_level(data: List[str]) -> ColourLevel:
        """
        Converts list of str to ColourLevel.
        """
        return ColourLevel(
                    room_id= data[1],
                    channel_id= data[2],
                    type= data[3],
                    level= data[4],
                    red_or_kelvin= data[4],
                    green= data[5],
                    blue= data[6].rstrip()
                )

    @staticmethod
    def _to_level(data: List[str]) -> Level:
        """
        Converts list of str to Level.
        """
        return Level(
                    room_id= data[1],
                    channel_id= data[2],
                    current_scene= data[3],
                    current_level= data[4],
                    target_level= data[5].rstrip()
                )

    @staticmethod
    def _to_room(data: List[str]) -> Room:
        """
        Converts list of str to Room.
        """
        return Room(
                    room_id= data[1], 
                    room_tile= data[2], 
                    room_type= data[3], 
                    room_mode= data[4].rstrip()
                )

    @staticmethod   
    def _to_scene(data: List[str]) -> Scene:
        """
        Converts list of str to Scene.
        """
        return Scene(
                    room_id= data[1],
                    scene_id= data[2],
                    scene_title= data[3].rstrip()
                )