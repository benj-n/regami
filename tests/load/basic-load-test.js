import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 10 },  // Ramp up to 10 users
    { duration: '5m', target: 10 },  // Stay at 10 users
    { duration: '2m', target: 50 },  // Ramp up to 50 users
    { duration: '5m', target: 50 },  // Stay at 50 users
    { duration: '2m', target: 100 }, // Ramp up to 100 users
    { duration: '5m', target: 100 }, // Stay at 100 users
    { duration: '5m', target: 0 },   // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'], // 95% < 500ms, 99% < 1s
    http_req_failed: ['rate<0.01'],                  // Error rate < 1%
    errors: ['rate<0.1'],                            // Custom error rate < 10%
  },
};

// Base URL - can be overridden with -e BASE_URL=
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Test data - these are seeded test accounts created by backend/scripts/seed.py
// Do NOT use these credentials in production. They are for load testing only.
const testUsers = [
  { email: 'alice@example.com', password: 'password123' },
  { email: 'bob@example.com', password: 'password123' },
  { email: 'carol@example.com', password: 'password123' },
];

// Helper function to get a random test user
function getRandomUser() {
  return testUsers[Math.floor(Math.random() * testUsers.length)];
}

// Helper function to login and get JWT token
function login() {
  const user = getRandomUser();

  const loginRes = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({
      email: user.email,
      password: user.password,
    }),
    {
      headers: { 'Content-Type': 'application/json' },
    }
  );

  check(loginRes, {
    'login successful': (r) => r.status === 200,
    'has access token': (r) => r.json('access_token') !== undefined,
  }) || errorRate.add(1);

  if (loginRes.status === 200) {
    return loginRes.json('access_token');
  }

  return null;
}

// Main test scenario
export default function () {
  // Get authentication token
  const token = login();
  if (!token) {
    sleep(1);
    return;
  }

  const authHeaders = {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  };

  // Test 1: Get current user profile
  group('User Profile', () => {
    const userRes = http.get(`${BASE_URL}/users/me`, authHeaders);

    check(userRes, {
      'get user profile successful': (r) => r.status === 200,
      'user has email': (r) => r.json('email') !== undefined,
    }) || errorRate.add(1);

    sleep(1);
  });

  // Test 2: List dogs
  group('Dog Listings', () => {
    const dogsRes = http.get(`${BASE_URL}/dogs/`, authHeaders);

    check(dogsRes, {
      'list dogs successful': (r) => r.status === 200,
      'dogs is array': (r) => Array.isArray(r.json()),
    }) || errorRate.add(1);

    sleep(1);
  });

  // Test 3: Search availability offers
  group('Availability Search', () => {
    const offersRes = http.get(`${BASE_URL}/availability/offers`, authHeaders);

    check(offersRes, {
      'list offers successful': (r) => r.status === 200,
      'offers is array': (r) => Array.isArray(r.json()),
    }) || errorRate.add(1);

    sleep(1);
  });

  // Test 4: Get matches
  group('Matches', () => {
    const matchesRes = http.get(`${BASE_URL}/matches/`, authHeaders);

    check(matchesRes, {
      'list matches successful': (r) => r.status === 200,
      'matches is array': (r) => Array.isArray(r.json()),
    }) || errorRate.add(1);

    sleep(1);
  });

  // Test 5: Get messages
  group('Messages', () => {
    const messagesRes = http.get(`${BASE_URL}/messages/`, authHeaders);

    check(messagesRes, {
      'list messages successful': (r) => r.status === 200,
      'messages is array': (r) => Array.isArray(r.json()),
    }) || errorRate.add(1);

    sleep(1);
  });

  // Test 6: Get notifications
  group('Notifications', () => {
    const notificationsRes = http.get(`${BASE_URL}/notifications/`, authHeaders);

    check(notificationsRes, {
      'list notifications successful': (r) => r.status === 200,
      'notifications is array': (r) => Array.isArray(r.json()),
    }) || errorRate.add(1);

    sleep(1);
  });

  sleep(Math.random() * 3 + 2); // Random sleep between 2-5 seconds
}

// Setup function - runs once before all VUs
export function setup() {
  // Health check
  const healthRes = http.get(`${BASE_URL}/health`);

  if (healthRes.status !== 200) {
    throw new Error(`API health check failed: ${healthRes.status}`);
  }

  console.log('API is healthy, starting load test...');

  return { startTime: new Date() };
}

// Teardown function - runs once after all VUs finish
export function teardown(data) {
  const endTime = new Date();
  const duration = (endTime - data.startTime) / 1000;

  console.log(`Load test completed in ${duration} seconds`);
}
