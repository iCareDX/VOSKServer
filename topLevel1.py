import argparse
import asyncio
import queue
import sounddevice as sd
import websockets
import json

async def run_test():
    async with websockets.connect(args.uri) as websocket_asr, \
               websockets.connect(args.llm_uri) as websocket_llm:
        with sd.RawInputStream(samplerate=args.samplerate, blocksize=4000, device=args.device, dtype='int16',
                               channels=1, callback=callback) as device:
            await websocket_asr.send(json.dumps({"config": {"sample_rate": device.samplerate}}))

            while True:
                data = await audio_queue.get()
                await websocket_asr.send(data)
                result = await websocket_asr.recv()
                result_json = json.loads(result)
                if 'text' in result_json:
                    recognized_text = result_json['text']
                    print("Recognized Text:", recognized_text)
                    
                    # Send recognized text to LLM WebSocket
                    await websocket_llm.send(recognized_text)
                    llm_response = await websocket_llm.recv()
                    print("LLM Response:", llm_response)

            await websocket_asr.send('{"eof" : 1}')
            print("Final result:")
            final_result = await websocket_asr.recv()
            print(final_result)

def callback(indata, frames, time, status):
    """Callback function to receive audio data and put it in a queue."""
    loop.call_soon_threadsafe(audio_queue.put_nowait, bytes(indata))

async def main():
    global args
    global loop
    global audio_queue

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-l', '--list-devices', action='store_true',
                        help='show list of audio devices and exit')
    args, remaining = parser.parse_known_args()
    if args.list_devices:
        print(sd.query_devices())
        parser.exit(0)
    parser = argparse.ArgumentParser(description="ASR Server",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     parents=[parser])
    parser.add_argument('-u', '--uri', type=str, metavar='URL',
                        help='ASR Server URL', default='ws://localhost:2700')
    parser.add_argument('-l', '--llm_uri', type=str, metavar='URL',
                        help='LLM Server URL', default='ws://localhost:8765')
    parser.add_argument('-d', '--device', type=int_or_str,
                        help='input device (numeric ID or substring)')
    parser.add_argument('-r', '--samplerate', type=int, help='sampling rate', default=16000)
    args = parser.parse_args(remaining)
    loop = asyncio.get_running_loop()
    audio_queue = asyncio.Queue()

    logging.basicConfig(level=logging.INFO)
    await run_test()

if __name__ == '__main__':
    asyncio.run(main())
