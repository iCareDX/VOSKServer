import asyncio
import websockets
import subprocess

async def handle_connection(websocket, path):
    async for message in websocket:
        print(f"Received message: {message}")
        # Call Aquestalk TTS
        subprocess.run(f'echo "{message}" | aquestalkpi -b -v f -', shell=True, check=True)
        # Send completion signal
        await websocket.send("TTS complete")

async def main():
    async with websockets.serve(handle_connection, "localhost", 8766):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
