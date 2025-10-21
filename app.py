from flask import Flask, jsonify, request

app = Flask(__name__)

# Prosta baza danych w pamięci
tasks = []

@app.route('/')
def home():
    return jsonify({
        'message': 'Flask Docker API',
        'version': '1.0.0',
        'endpoints': ['/health', '/api/tasks']
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

@app.route('/api/tasks', methods=['GET', 'POST'])
def handle_tasks():
    if request.method == 'GET':
        return jsonify({'tasks': tasks, 'count': len(tasks)})

    if request.method == 'POST':
        task = request.get_json()
        if task and 'title' in task:
            task['id'] = len(tasks) + 1
            tasks.append(task)
            return jsonify(task), 201
        return jsonify({'error': 'Invalid task data'}), 400

@app.route('/api/tasks/<int:task_id>', methods=['GET', 'DELETE'])
def handle_task(task_id):
    task = next((t for t in tasks if t['id'] == task_id), None)

    if request.method == 'GET':
        if task:
            return jsonify(task)
        return jsonify({'error': 'Task not found'}), 404

    if request.method == 'DELETE':
        if task:
            tasks.remove(task)
            return jsonify({'message': 'Task deleted'}), 200
        return jsonify({'error': 'Task not found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
