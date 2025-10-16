import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '10m', target: 200 },  // Ramp up to 200 users over 10 minutes
    { duration: '1h', target: 200 },   // Stay at 200 users for 1 hour
    { duration: '10m', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<1000'],
    http_req_failed: ['rate<0.05'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  // Simulate realistic user behavior
  const token = login();
  if (!token) return;

  // Browse dogs (70% of users)
  if (Math.random() < 0.7) {
    browseDogs(token);
  }

  // Check messages (50% of users)
  if (Math.random() < 0.5) {
    checkMessages(token);
  }

  // Search availability (40% of users)
  if (Math.random() < 0.4) {
    searchAvailability(token);
  }

  sleep(Math.random() * 10 + 5); // 5-15 seconds between actions
}

function login() {
  const res = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({
      email: 'alice@example.com',
      password: 'password123',
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );

  return res.status === 200 ? res.json('access_token') : null;
}

function browseDogs(token) {
  const res = http.get(`${BASE_URL}/dogs/`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  check(res, { 'browse dogs ok': (r) => r.status === 200 }) || errorRate.add(1);
  sleep(2);
}

function checkMessages(token) {
  const res = http.get(`${BASE_URL}/messages/`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  check(res, { 'check messages ok': (r) => r.status === 200 }) || errorRate.add(1);
  sleep(1);
}

function searchAvailability(token) {
  const res = http.get(`${BASE_URL}/availability/offers`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  check(res, { 'search availability ok': (r) => r.status === 200 }) || errorRate.add(1);
  sleep(3);
}
