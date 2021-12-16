from gpiozero import Button, LED
from decouple import config
import AccessControl.Functions.matrix_functions as mx
import AccessControl.Functions.functions as func
import asyncio
import time

#Parar el programa hasta que el pin se ponga high, si pasa un tiempo depsues del high se tiene que correr el audio

async def main():
    server = config('MATRIX_SERVER')
    user = config('MATRIX_USER')
    password = config('MATRIX_PASSWORD')
    device_id = config('MATRIX_DEVICE_ID')
    room = config('MATRIX_ROOM_NAME_SPEAKER')
    el_pin = Button(26, pull_up=False)

    alarm_task = asyncio.create_task(
        mx.matrix_login(server, user, password, device_id))
    alarm = await alarm_task

    room_id_task = asyncio.create_task(mx.matrix_get_room_id(alarm,room))
    room_id = await room_id_task

    change = True

    while True:
        time.sleep(1)
        #has_time_passed para enviar el mensaje, no se puede parar como un mojiganga el programa
        if el_pin.is_active: #la puerta se abrio
            if change:
                time_msg = time.time()
                change = False
            elif func.has_time_passed(time_msg, 5):
                await mx.matrix_send_message(alarm, room_id, 'ALARM')
        elif not change:
            await mx.matrix_send_message(alarm, room_id, 'STOP')
            change = True
        



