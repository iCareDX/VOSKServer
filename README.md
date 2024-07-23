# Server-based Integration of STT(Speech-To-Text), LLM, TTS(Text-To-Speech) 

##First start the three servers:
asr_server.py
llm_server.py
aques_server.py

##Then start the toplevel
toplevel.py

#Browser
toplevel_browser.py


# VOSKServer
Speech to text server by VOSK

オリジナルバージョン
下記のペアで動作します．
asr_server === test_microphone.py

無音区間検出バージョン
下記のペアで動作します．
asr_server2 === test_microphone3.py

無音検出のパラメータ調整が難しいので，オリジナルバージョン（何もしない）の方が良いかもしれません．
