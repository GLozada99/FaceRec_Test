from nio import AsyncClient


async def matrix_login(server, user, password, device_id=None):
    if device_id:
        client = AsyncClient(server, user, device_id)
    else:
        client = AsyncClient(server, user)
    await client.login(password)
    return client


async def matrix_get_room_id(client, room_name):
    response = await client.room_resolve_alias(room_name)
    return response.room_id


async def matrix_send_message(client, room_id, message):
    await client.room_send(
        room_id=room_id,
        message_type="m.room.message",
        content={
            "body": message,
            "msgtype": "m.text"
        }
    )


async def matrix_get_messages(client, room_id, limit=1):
    messages = []
    response = await client.room_messages(room_id, client.next_batch, limit=limit)
    for eve in response.chunk:
        msg = eve.body
        timestamp_miliseconds = int(eve.server_timestamp)
        timestamp_seconds = float(timestamp_miliseconds / 1000)
        messages.append((msg, timestamp_seconds, eve.event_id))

    return messages


async def matrix_logout_close(client):
    await client.logout()
    await client.close()
