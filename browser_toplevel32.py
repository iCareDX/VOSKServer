import argparse
import asyncio
import queue
import sounddevice as sd
import websockets
import json
import logging
import re
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# Flask アプリケーションのセットアップ
app = Flask(__name__)
socketio = SocketIO(app)

# グローバル変数として認識されたテキストと LLM 応答の履歴を保存する
recognized_text_history = []
llm_response_history = []

@app.route('/')
def index():
    return render_template('index.html', recognized_text_history=recognized_text_history, llm_response_history=llm_response_history)

def start_flask_app():
    socketio.run(app, port=5000)

# 音声処理関連の初期設定
is_speaking = False
ignore_word = ["あ", "あー", "え", "えー", "えーと", "う", "うん", "ん"]

def int_or_str(text):
    try:
        return int(text)
    except ValueError:
        return text

def callback(indata, frames, time, status):
    if not is_speaking:
        loop.call_soon_threadsafe(audio_queue.put_nowait, bytes(indata))

async def send_to_tts(websocket_tts, text):
    global is_speaking
    is_speaking = True
    text = text.strip()
    print(f"TTS send data: {text}")
    try:
        await websocket_tts.send(text)
        await websocket_tts.recv()
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection closed error: {e}. Reconnecting...")
        websocket_tts = await websockets.connect(args.tts_uri)
        await websocket_tts.send(text)
        await websocket_tts.recv()
    finally:
        is_speaking = False
        print("TTS completed")

async def toploop():
    global is_speaking, recognized_text_history, llm_response_history

    with sd.RawInputStream(samplerate=args.samplerate, blocksize=4000, device=args.device, dtype='int16',
                           channels=1, callback=callback) as device:
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
                    
                    if not isinstance(recognized_text, str):
                        recognized_text = str(recognized_text)
                    
                    if recognized_text not in ignore_word:
                        # LLM サーバーにテキストを送信
                        await websocket_llm.send(recognized_text)
                        llm_response = await websocket_llm.recv()
                        
                        # 履歴に保存
                        recognized_text_history.append(recognized_text)
                        llm_response_history.append(llm_response)
                        
                        # Web ページにリアルタイムでデータを送信
                        socketio.emit('update_text', {
                            'recognized_text': recognized_text, 
                            'llm_response': llm_response,
                            'recognized_text_history': recognized_text_history,
                            'llm_response_history': llm_response_history
                        })
                        
                        print("LLM Response:", llm_response)
                        
                        # 文章ごとに分割し、TTS サーバーに送信
                        sentences = re.split(r'(?<=[.!?。])\s+', llm_response)
                        print(f"Split sentences: {sentences}")
                        for sentence in sentences:
                            if sentence:
                                await send_to_tts(websocket_tts, sentence)

                if 'final' in result_json and result_json['final']:
                    break

            await websocket_asr.send('{"eof" : 1}')
            print("Final result:")
            final_result = await websocket_asr.recv()
            print(final_result)

async def main():
    global args, loop, audio_queue

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-d', '--list-devices', action='store_true', help='show list of audio devices and exit')
    args, remaining = parser.parse_known_args()
    if args.list_devices:
        print(sd.query_devices())
        parser.exit(0)
    parser = argparse.ArgumentParser(description="ASR Server",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     parents=[parser])
    parser.add_argument('-a', '--uri', type=str, metavar='URL', help='ASR Server URL', default='ws://localhost:2700')
    parser.add_argument('-l', '--llm_uri', type=str, metavar='URL', help='LLM Server URL', default='ws://localhost:8765')
    parser.add_argument('-t', '--tts_uri', type=str, metavar='URL', help='TTS Server URL', default='ws://localhost:8766')
    parser.add_argument('-i', '--device', type=int_or_str, help='input device (numeric ID or substring)')
    parser.add_argument('-r', '--samplerate', type=int, help='sampling rate', default=16000)
    args = parser.parse_args(remaining)
    loop = asyncio.get_running_loop()
    audio_queue = asyncio.Queue()

    logging.basicConfig(level=logging.INFO)
    await toploop()

if __name__ == '__main__':
    # Flask-SocketIO サーバーを別スレッドで起動
    flask_thread = threading.Thread(target=start_flask_app)
    flask_thread.start()

    # WebSocket メイン処理の開始
    asyncio.run(main())
