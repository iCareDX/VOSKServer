#!/usr/bin/env python3

import json
import os
import sys
import asyncio
import websockets
import concurrent.futures
import logging
from vosk import Model, SpkModel, KaldiRecognizer

def process_chunk(rec, message):
    if message == b'{"eof" : 1}':
        return rec.FinalResult(), True
    if message == b'{"reset" : 1}':
        return rec.FinalResult(), False
    elif rec.AcceptWaveform(message):
        return rec.Result(), False
    else:
        return rec.PartialResult(), False

async def recognize(websocket, path):
    global model
    global spk_model
    global args
    global pool

    loop = asyncio.get_running_loop()
    rec = None
    phrase_list = None
    sample_rate = args.sample_rate
    show_words = args.show_words
    max_alternatives = args.max_alternatives
    model_changed = False

    logging.info('Connection from %s', websocket.remote_address);

    try:
        while True:
            try:
                message = await websocket.recv()
            except websockets.exceptions.ConnectionClosed as e:
                logging.warning(f"WebSocket connection closed: {e}")
                break

            # Handle configuration messages
            if isinstance(message, str) and 'config' in message:
                jobj = json.loads(message)['config']
                logging.info("Config %s", jobj)
                if 'phrase_list' in jobj:
                    phrase_list = jobj['phrase_list']
                if 'sample_rate' in jobj:
                    sample_rate = float(jobj['sample_rate'])
                if 'model' in jobj:
                    model = Model(jobj['model'])
                    model_changed = True
                if 'words' in jobj:
                    show_words = bool(jobj['words'])
                if 'max_alternatives' in jobj:
                    max_alternatives = int(jobj['max_alternatives'])
                continue

            # Create or update the recognizer
            if not rec or model_changed:
                model_changed = False
                if phrase_list:
                    rec = KaldiRecognizer(model, sample_rate, json.dumps(phrase_list, ensure_ascii=False))
                else:
                    rec = KaldiRecognizer(model, sample_rate)
                rec.SetWords(show_words)
                rec.SetMaxAlternatives(max_alternatives)
                if spk_model:
                    rec.SetSpkModel(spk_model)

            # Ensure message is bytes for audio data
            if isinstance(message, str):
                message = message.encode('utf-8')

            response, stop = await loop.run_in_executor(pool, process_chunk, rec, message)
            await websocket.send(response)
            if stop:
                break

    except Exception as e:
        logging.error(f"Error in WebSocket handler: {e}")

    finally:
        await websocket.close()

async def start():
    global model
    global spk_model
    global args
    global pool

    logging.basicConfig(level=logging.INFO)

    args = type('', (), {})()

    args.interface = os.environ.get('VOSK_SERVER_INTERFACE', '0.0.0.0')
    args.port = int(os.environ.get('VOSK_SERVER_PORT', 2700))
    args.model_path = os.environ.get('VOSK_MODEL_PATH', 'model')
    args.spk_model_path = os.environ.get('VOSK_SPK_MODEL_PATH')
    args.sample_rate = float(os.environ.get('VOSK_SAMPLE_RATE', 8000))
    args.max_alternatives = int(os.environ.get('VOSK_ALTERNATIVES', 0))
    args.show_words = bool(os.environ.get('VOSK_SHOW_WORDS', True))

    if len(sys.argv) > 1:
       args.model_path = sys.argv[1]

    model = Model(lang="ja")
    spk_model = SpkModel(args.spk_model_path) if args.spk_model_path else None

    pool = concurrent.futures.ThreadPoolExecutor((os.cpu_count() or 1))

    async with websockets.serve(recognize, args.interface, args.port):
        await asyncio.Future()

if __name__ == '__main__':
    asyncio.run(start())
