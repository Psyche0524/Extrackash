from rest_framework.test import APITestCase


class AuthTests(APITestCase):
    def test_register_login_logout(self):
        r = self.client.post('/api/auth/register/', {
            'username': 'juan', 'email': 'juan@example.com', 'password': 'StrongPass#2026'})
        self.assertEqual(r.status_code, 201)
        self.assertNotIn('password', r.data)

        r = self.client.post('/api/auth/login/', {'username': 'juan', 'password': 'StrongPass#2026'})
        self.assertEqual(r.status_code, 200)
        access, refresh = r.data['access'], r.data['refresh']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 200)
        self.assertEqual(self.client.post('/api/auth/logout/', {'refresh': refresh}).status_code, 205)

    def test_weak_password_rejected(self):
        r = self.client.post('/api/auth/register/', {
            'username': 'juan', 'email': 'juan@example.com', 'password': '123'})
        self.assertEqual(r.status_code, 400)

    def test_duplicate_email_rejected(self):
        data = {'username': 'a', 'email': 'same@example.com', 'password': 'StrongPass#2026'}
        self.client.post('/api/auth/register/', data)
        data['username'] = 'b'
        self.assertEqual(self.client.post('/api/auth/register/', data).status_code, 400)

    def test_wrong_password_rejected(self):
        self.client.post('/api/auth/register/', {
            'username': 'juan', 'email': 'juan@example.com', 'password': 'StrongPass#2026'})
        r = self.client.post('/api/auth/login/', {'username': 'juan', 'password': 'wrong'})
        self.assertEqual(r.status_code, 401)
