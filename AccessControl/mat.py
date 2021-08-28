import asyncio
import AccessControl.Functions.functions as func
import AccessControl.Functions.matrix_functions as mx
from nio import RoomMessageText, AsyncClient
import time


async def main():
    server = 'https://matrix-client.matrix.org'
    user = '@tavo9:matrix.org'
    password = 'O1KhpTBn7D47'
    device_id = 'LYTVJFQRJG'
    room_1 = '#temper:matrix.org'
    room_2 = '#speaker:matrix.org'
    client_task = asyncio.create_task(
        mx.matrix_login(server, user, password, device_id))
    client = await client_task

    room_id_task1 = asyncio.create_task(
        mx.matrix_get_room_id(client, room_1))
    room_id_1 = await room_id_task1

    room_id_task2 = asyncio.create_task(
        mx.matrix_get_room_id(client, room_2))
    room_id_2 = await room_id_task2
    i = 0
    while (True):

        messages_task = asyncio.create_task(
            mx.matrix_get_messages(client, room_1))
        data = (await messages_task)

        data_tem = data[room_id_1]
        data_sp = data[room_id_2]

        if data_tem and i % 2 == 0:
            print('Temperature', data_tem)

        if data_sp and i % 20 == 0:
            print('Speaker', data_sp)

        time.sleep(0.2)
        i += 1
        print(i)

    # if len(sync_response.rooms.join) > 0:

    # joins = sync_response.rooms.join
    # for room_id in joins:
    #     for event in joins[room_id].timeline.events:
    #         print(event)


async def main2():
    server = 'https://matrix-client.matrix.org'
    user = '@tavo9:matrix.org'
    password = 'O1KhpTBn7D47'
    device_id = 'LYTVJFQRJG'
    room_1 = '#temper:matrix.org'
    room_2 = '#speaker:matrix.org'

    client_task = asyncio.create_task(
        mx.matrix_login(server, user, password, device_id))
    client = await client_task

    room_id_task1 = asyncio.create_task(
        mx.matrix_get_room_id(client, room_1))
    room_id_1 = await room_id_task1

    room_id_task2 = asyncio.create_task(
        mx.matrix_get_room_id(client, room_2))
    room_id_2 = await room_id_task2
    while True:
        x = await client.room_messages(room_id_1, client.next_batch, limit=2)
        for msg in x.chunk:
            print(msg.body)

        y = await client.room_messages(room_id_2, client.next_batch, limit=2)
        for msg in y.chunk:
            print(msg.body)
        time.sleep(0.4)

    await mx.matrix_logout_close(client)

if __name__ == '__main__':
    asyncio.run(main2())
