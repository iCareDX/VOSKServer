#!/usr/bin/env python3

import json
import os
import sys
import asyncio
import websockets
import logging
import sounddevice as sd
import argparse
import webrtcvad
import time

def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text

def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    loop.call_soon_threadsafe(audio_queue.put_nowait, bytes(indata))

async def run_test():
    vad = webrtcvad.Vad()
    vad.set_mode(3)  # Set to very aggressive mode

    frame_duration = 30  # Frame duration in ms (10, 20, 30)
    frame_samples = int(args.samplerate * frame_duration / 1000)  # Number of samples per frame
    frame_bytes = frame_samples * 2  # Frame size in bytes (2 bytes per sample for 'int16')

    silence_threshold = 2.0  # Threshold for continuous silence in seconds
    silence_start_time = None

    with sd.RawInputStream(samplerate=args.samplerate, blocksize=frame_samples, device=args.device, dtype='int16',
                           channels=1, callback=callback):
        try:
            async with websockets.connect(args.uri) as websocket:
                config_message = json.dumps({"config": {"sample_rate": args.samplerate}})
                await websocket.send(config_message)
                print(f"Sent config: {config_message}")

                while True:
                    data = await audio_queue.get()

                    # Ensure data length matches frame size
                    if len(data) == frame_bytes:
                        is_speech = vad.is_speech(data, args.samplerate)
                        if is_speech:
                            print("Speech detected")
                            silence_start_time = None  # Reset silence timer
                            await websocket.send(data)
                            response = await websocket.recv()
                            print(response)
                        else:
                            if silence_start_time is None:
                                silence_start_time = time.time()  # Start silence timer
                            elif time.time() - silence_start_time > silence_threshold:
                                print("Silence threshold reached, sending EOF")
                                eof_message = json.dumps({"eof": 1})
                                await websocket.send(eof_message)
                                print(f"Sent EOF: {eof_message}")
                                await asyncio.sleep(1)  # Wait for the server to process EOF
                                try:
                                    final_response = await websocket.recv()
                                    print("Final response:", final_response)
                                except websockets.exceptions.ConnectionClosedError as e:
                                    print(f"WebSocket connection closed with error: {e}")
                                silence_start_time = time.time()  # Reset silence timer after sending EOF
                            #print("Silence detected")
                            pass
                    else:
                        print(f"Incorrect frame size: {len(data)} bytes, expected {frame_bytes} bytes")

        except websockets.exceptions.ConnectionClosedError as e:
            print(f"WebSocket connection closed with error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            await websocket.close()

async def main():
    global args
    global loop
    global audio_queue

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-l', '--list-devices', action='store_true', help='show list of audio devices and exit')
    args, remaining = parser.parse_known_args()
    if args.list_devices:
        print(sd.query_devices())
        parser.exit(0)
    parser = argparse.ArgumentParser(description="ASR Server",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     parents=[parser])
    parser.add_argument('-u', '--uri', type=str, metavar='URL', help='Server URL', default='ws://localhost:2700')
    parser.add_argument('-d', '--device', type=int_or_str, help='input device (numeric ID or substring)')
    parser.add_argument('-r', '--samplerate', type=int, help='sampling rate', default=16000)
    args = parser.parse_args(remaining)
    loop = asyncio.get_running_loop()
    audio_queue = asyncio.Queue()

    logging.basicConfig(level=logging.INFO)
    await run_test()

if __name__ == '__main__':
    asyncio.run(main())
