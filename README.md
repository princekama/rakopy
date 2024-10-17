# RakoPy
RakoPy is a Python library that allows you to control [Rako Controls](https://rakocontrols.com) system programmatically.

The library has been tested with Rako [WK-HUB](https://rakocontrols.com/wkhub/) but it should also work with [RK-HUB](https://rakocontrols.com/rkhub/).


## Installation
```
pip install rakopy
```

## Usage
```python
import asyncio

from rakopy.hub import Hub

async def main():
    client_name = "client_name"
    host = "192.168.1.42"
    hub = Hub(client_name, host)
    response = await hub.get_rooms()

asyncio.run(main())
```

## License
RakoPy is released under the [MIT license](https://github.com/princekama/rakopy/blob/main/LICENSE).
