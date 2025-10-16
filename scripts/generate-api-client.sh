#!/bin/bash

# Generate TypeScript API client from OpenAPI schema
# This script extracts the OpenAPI schema from the running API and generates TypeScript types

set -e

API_URL="${API_URL:-http://localhost:8000}"
OUTPUT_DIR="web/src/api/generated"

echo "Generating TypeScript API client..."
echo "API URL: $API_URL"
echo "Output: $OUTPUT_DIR"

# Check if API is running
if ! curl -s "${API_URL}/health" > /dev/null; then
    echo "Error: API is not running at ${API_URL}"
    echo "Start the API server first: uvicorn app.main:app --app-dir backend"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Download OpenAPI schema
echo "Downloading OpenAPI schema..."
curl -s "${API_URL}/openapi.json" > "${OUTPUT_DIR}/openapi.json"

# Generate TypeScript types using openapi-typescript
echo "Generating TypeScript types..."
cd web
npx openapi-typescript ../backend/app/openapi.json -o src/api/generated/schema.d.ts

# Generate API client using openapi-fetch
echo "Generating API client..."
cat > src/api/generated/client.ts << 'EOF'
import createClient from 'openapi-fetch';
import type { paths } from './schema';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const client = createClient<paths>({
  baseUrl: API_BASE_URL,
});

// Add auth token to all requests
let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;

  if (token) {
    client.use({
      onRequest({ request }) {
        request.headers.set('Authorization', `Bearer ${token}`);
        return request;
      },
    });
  }
}

// Get current auth token
export function getAuthToken(): string | null {
  return authToken;
}

// Clear auth token
export function clearAuthToken() {
  authToken = null;
}

// Convenience methods for common operations
export const api = {
  // Auth
  async login(email: string, password: string) {
    const { data, error } = await client.POST('/auth/login', {
      body: { email, password },
    });

    if (data?.access_token) {
      setAuthToken(data.access_token);
    }

    return { data, error };
  },

  async register(email: string, password: string, full_name: string) {
    const { data, error } = await client.POST('/auth/register', {
      body: { email, password, full_name },
    });

    if (data?.access_token) {
      setAuthToken(data.access_token);
    }

    return { data, error };
  },

  async logout() {
    clearAuthToken();
  },

  // Users
  async getCurrentUser() {
    return client.GET('/users/me');
  },

  async updateProfile(data: any) {
    return client.PUT('/users/me', { body: data });
  },

  // Dogs
  async listDogs() {
    return client.GET('/dogs/');
  },

  async getDog(id: number) {
    return client.GET('/dogs/{dog_id}', { params: { path: { dog_id: id } } });
  },

  async createDog(data: any) {
    return client.POST('/dogs/', { body: data });
  },

  async updateDog(id: number, data: any) {
    return client.PUT('/dogs/{dog_id}', {
      params: { path: { dog_id: id } },
      body: data,
    });
  },

  async deleteDog(id: number) {
    return client.DELETE('/dogs/{dog_id}', {
      params: { path: { dog_id: id } },
    });
  },

  // Availability
  async listAvailabilityOffers() {
    return client.GET('/availability/offers');
  },

  async createAvailabilityOffer(data: any) {
    return client.POST('/availability/offers', { body: data });
  },

  async listAvailabilityRequests() {
    return client.GET('/availability/requests');
  },

  async createAvailabilityRequest(data: any) {
    return client.POST('/availability/requests', { body: data });
  },

  // Matches
  async listMatches() {
    return client.GET('/matches/');
  },

  async createMatch(data: any) {
    return client.POST('/matches/', { body: data });
  },

  async confirmMatch(id: number) {
    return client.POST('/matches/{match_id}/confirm', {
      params: { path: { match_id: id } },
    });
  },

  // Messages
  async listMessages(userId?: number) {
    return client.GET('/messages/', {
      params: { query: { user_id: userId } },
    });
  },

  async sendMessage(receiverId: number, content: string) {
    return client.POST('/messages/', {
      body: { receiver_id: receiverId, content },
    });
  },

  // Notifications
  async listNotifications() {
    return client.GET('/notifications/');
  },

  async markNotificationRead(id: number) {
    return client.PUT('/notifications/{notification_id}/read', {
      params: { path: { notification_id: id } },
    });
  },

  async markAllNotificationsRead() {
    return client.PUT('/notifications/mark-all-read');
  },
};

export default api;
EOF

echo ""
echo "✓ TypeScript API client generated successfully!"
echo ""
echo "Files created:"
echo "  - ${OUTPUT_DIR}/openapi.json"
echo "  - ${OUTPUT_DIR}/schema.d.ts"
echo "  - ${OUTPUT_DIR}/client.ts"
echo ""
echo "Usage in your React components:"
echo ""
echo "  import api from '@/api/generated/client';"
echo ""
echo "  // Login"
echo "  const { data, error } = await api.login('user@example.com', 'password');"
echo ""
echo "  // Get current user"
echo "  const { data: user } = await api.getCurrentUser();"
echo ""
echo "  // List dogs"
echo "  const { data: dogs } = await api.listDogs();"
echo ""
