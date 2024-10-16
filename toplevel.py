import argparse
import asyncio
import queue
import sounddevice as sd
import websockets
import json
import logging
import re

is_speaking = False

def int_or_str(text):
    """Helper function for argument parsing to handle integers and strings."""
    try:
        return int(text)
    except ValueError:
        return text

def callback(indata, frames, time, status):
    """Callback function to receive audio data and put it in a queue."""
    if not is_speaking:
        loop.call_soon_threadsafe(audio_queue.put_nowait, bytes(indata))

async def send_to_tts(websocket_tts, text):
    """Send text to TTS server and wait for completion signal."""
    global is_speaking
    is_speaking = True
    text = text.strip()  # Remove any leading/trailing whitespace and newlines
    print(f"TTS send data: {text}")
    await websocket_tts.send(text)
    await websocket_tts.recv()  # Wait for TTS completion signal
    is_speaking = False
    print("TTS completed")

async def process_llm_response(websocket_llm, websocket_tts, recognized_text):
    """Send recognized text to LLM WebSocket and process the response."""
    try:
        print(f"Sending to LLM: {recognized_text}")
        await websocket_llm.send(recognized_text)
        llm_response = await websocket_llm.recv()
        print("LLM Response:", llm_response)

        # Split LLM response into sentences and send to TTS
        #sentences = re.split(r'(?<=[.!?。])\s+', llm_response)
        sentences = re.split(r'(?<=[,.，。？！])\s*|\n', llm_response)
        print(f"Split sentences: {sentences}")
        for sentence in sentences:
            if sentence:  # Ensure not to send empty strings
                await send_to_tts(websocket_tts, sentence)
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"LLM WebSocket connection closed: {e}")
        raise e

async def run_test():
    global is_speaking

    with sd.RawInputStream(samplerate=args.samplerate, blocksize=4000, device=args.device, dtype='int16',
                           channels=1, callback=callback) as device:
        try:
            async with websockets.connect(args.uri) as websocket_asr, \
                       websockets.connect(args.llm_uri) as websocket_llm, \
                       websockets.connect(args.tts_uri) as websocket_tts:
                print(f"Connected to ASR server at {args.uri}")
                print(f"Connected to LLM server at {args.llm_uri}")
                print(f"Connected to TTS server at {args.tts_uri}")
                
                await websocket_asr.send(json.dumps({"config": {"sample_rate": device.samplerate}}))

                while True:
                    data = await audio_queue.get()
                    await websocket_asr.send(data)
                    result = await websocket_asr.recv()
                    result_json = json.loads(result)
                    
                    if 'result' in result_json:
                        recognized_text_list = result_json['result']
                        recognized_text = ' '.join([word_info['word'] for word_info in recognized_text_list])
                        print("Final Recognized Text:", recognized_text)
                        
                        # Ensure recognized_text is a string
                        if not isinstance(recognized_text, str):
                            recognized_text = str(recognized_text)
                        
                        # Process LLM response and handle errors
                        try:
                            await process_llm_response(websocket_llm, websocket_tts, recognized_text)
                        except websockets.exceptions.ConnectionClosedError as e:
                            print(f"Retrying LLM connection due to error: {e}")
                            async with websockets.connect(args.llm_uri) as websocket_llm:
                                await process_llm_response(websocket_llm, websocket_tts, recognized_text)

                    if 'final' in result_json and result_json['final']:
                        break

                await websocket_asr.send('{"eof" : 1}')
                print("Final result:")
                final_result = await websocket_asr.recv()
                print(final_result)
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"WebSocket connection closed: {e}")

async def main():
    global args
    global loop
    global audio_queue

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-d', '--list-devices', action='store_true',
                        help='show list of audio devices and exit')
    args, remaining = parser.parse_known_args()
    if args.list_devices:
        print(sd.query_devices())
        parser.exit(0)
    parser = argparse.ArgumentParser(description="ASR Server",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     parents=[parser])
    parser.add_argument('-a', '--uri', type=str, metavar='URL',
                        help='ASR Server URL', default='ws://localhost:2700')
    parser.add_argument('-l', '--llm_uri', type=str, metavar='URL',
                        help='LLM Server URL', default='ws://localhost:8765')
    parser.add_argument('-t', '--tts_uri', type=str, metavar='URL',
                        help='TTS Server URL', default='ws://localhost:8766')
    parser.add_argument('-i', '--device', type=int_or_str,
                        help='input device (numeric ID or substring)')
    parser.add_argument('-r', '--samplerate', type=int, help='sampling rate', default=16000)
    args = parser.parse_args(remaining)
    loop = asyncio.get_running_loop()
    audio_queue = asyncio.Queue()

    logging.basicConfig(level=logging.INFO)
    await run_test()

if __name__ == '__main__':
    asyncio.run(main())
