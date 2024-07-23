from flask import Flask, render_template
import threading

app = Flask(__name__)

recognition_result = ""
llm_response = ""

@app.route('/')
def index():
    global recognition_result, llm_response
    return render_template('index.html', recognition_result=recognition_result, llm_response=llm_response)

def run_flask():
    app.run(host='0.0.0.0', port=5770, debug=True, use_reloader=False)

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
