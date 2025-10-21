import unittest
import json
from app import app, tasks

class TestFlaskApp(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        tasks.clear()

    def tearDown(self):
        tasks.clear()

    def test_home_endpoint(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertIn('version', data)

    def test_health_endpoint(self):
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')

    def test_get_tasks_empty(self):
        response = self.app.get('/api/tasks')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['tasks'], [])

    def test_create_task(self):
        task_data = {'title': 'Test Task', 'description': 'Test Description'}
        response = self.app.post(
            '/api/tasks',
            data=json.dumps(task_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Test Task')
        self.assertIn('id', data)

    def test_create_task_invalid_data(self):
        response = self.app.post(
            '/api/tasks',
            data=json.dumps({}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_get_task_by_id(self):
        task_data = {'title': 'Test Task'}
        self.app.post(
            '/api/tasks',
            data=json.dumps(task_data),
            content_type='application/json'
        )

        response = self.app.get('/api/tasks/1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['id'], 1)

    def test_get_task_not_found(self):
        response = self.app.get('/api/tasks/999')
        self.assertEqual(response.status_code, 404)

    def test_delete_task(self):
        task_data = {'title': 'Test Task'}
        self.app.post(
            '/api/tasks',
            data=json.dumps(task_data),
            content_type='application/json'
        )

        response = self.app.delete('/api/tasks/1')
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/api/tasks')
        data = json.loads(response.data)
        self.assertEqual(data['count'], 0)

if __name__ == '__main__':
    unittest.main()
