# Regami Domain Configuration Summary

This document summarizes all domain-related configurations across the Regami project.

## Domain Structure

### Production Environment
- **Frontend:** `https://regami.com` and `https://www.regami.com`
- **API:** `https://api.regami.com`
- **CDN:** CloudFront distribution

### Staging Environment
- **Frontend:** `https://staging.regami.com`
- **API:** `https://api.staging.regami.com`
- **CDN:** CloudFront distribution

### Local Development
- **Frontend:** `http://localhost:5173`
- **API:** `http://localhost:8000`
- **Documentation:** `http://localhost:8000/docs`

---

## Updated Files

### 1. Backend Configuration

**File:** `backend/app/core/config.py`
```python
# Default CORS for local development
cors_origins: str = Field(default="http://localhost:5173,http://127.0.0.1:5173")

# Production validation ensures HTTPS and specific domains
# Staging allows both staging domain and localhost
```

**File:** `backend/app/main.py`
```python
# CORS middleware reads from settings.cors_origins
# Contact information updated to regami.com
contact={
    "name": "Regami Support",
    "url": "https://regami.com/support",
    "email": "support@regami.com",
}
```

### 2. Infrastructure Configuration

**File:** `infra/terraform-serverless/main.tf`

**API Gateway CORS:**
```hcl
cors_configuration {
  allow_origins = [
    "https://regami.com",
    "https://www.regami.com",
    "https://staging.regami.com",
    "http://localhost:5173",
    "http://127.0.0.1:5173"
  ]
  allow_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
  allow_headers = ["*"]
  allow_credentials = true
  max_age = 300
}
```

**Lambda Environment Variables:**
```hcl
environment {
  variables = {
    # ... other vars ...
    CORS_ORIGINS = var.environment == "prod"
      ? "https://regami.com,https://www.regami.com"
      : "https://staging.regami.com,http://localhost:5173"
  }
}
```

### 3. CI/CD Configuration

**File:** `.github/workflows/deploy-serverless.yml`

**Environment-based CORS:**
```yaml
# Determine environment
if [ "${{ github.ref }}" == "refs/heads/main" ]; then
  ENV="prod"
  CORS_ORIGINS="https://regami.com,https://www.regami.com"
  S3_BUCKET="regami-uploads-prod"
else
  ENV="staging"
  CORS_ORIGINS="https://staging.regami.com,http://localhost:5173"
  S3_BUCKET="regami-uploads-staging"
fi
```

### 4. Environment Files

**File:** `.env.example`
```bash
# For local development:
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# For staging:
# CORS_ORIGINS=https://staging.regami.com,http://localhost:5173

# For production:
# CORS_ORIGINS=https://regami.com,https://www.regami.com
```

**File:** `web/.env.example`
```bash
# For local development:
VITE_API_BASE_URL=http://localhost:8000

# For staging:
# VITE_API_BASE_URL=https://api.staging.regami.com

# For production:
# VITE_API_BASE_URL=https://api.regami.com
```

---

## Configuration by Environment

### Local Development

**Backend:**
```bash
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
APP_ENV=dev
```

**Frontend:**
```bash
VITE_API_BASE_URL=http://localhost:8000
```

**Testing:**
- Register at http://localhost:5173
- API docs at http://localhost:8000/docs
- No SSL required

---

### Staging Environment

**Backend Lambda Environment:**
```bash
CORS_ORIGINS=https://staging.regami.com,http://localhost:5173
APP_ENV=staging
S3_BUCKET=regami-uploads-staging
SECRET_KEY=[staging-specific-key]
DATABASE_URL=[staging-database]
```

**Frontend Build:**
```bash
VITE_API_BASE_URL=https://api.staging.regami.com
```

**DNS Records (Route 53):**
```
staging.regami.com        A       ALIAS to CloudFront
api.staging.regami.com    CNAME   API Gateway endpoint
```

**Testing:**
- Access at https://staging.regami.com
- API at https://api.staging.regami.com
- SSL certificate required (ACM)
- Can still test locally against staging API

---

### Production Environment

**Backend Lambda Environment:**
```bash
CORS_ORIGINS=https://regami.com,https://www.regami.com
APP_ENV=prod
S3_BUCKET=regami-uploads-prod
SECRET_KEY=[production-key]
DATABASE_URL=[production-database]
SENTRY_DSN=[production-sentry]
```

**Frontend Build:**
```bash
VITE_API_BASE_URL=https://api.regami.com
```

**DNS Records (Route 53):**
```
regami.com                A       ALIAS to CloudFront
www.regami.com            A       ALIAS to CloudFront
api.regami.com            CNAME   API Gateway endpoint
```

**Security:**
- SSL certificate required (ACM)
- HTTPS only (HTTP redirects to HTTPS)
- Strict CORS (no wildcards)
- No localhost origins

---

## SSL/TLS Certificates

### Production Certificate
```bash
# IMPORTANT: ACM certificates for CloudFront MUST be in us-east-1 region
# This is a CloudFront requirement - all other resources will be in ca-central-1
# Request certificate in us-east-1 (CloudFront requirement)
aws acm request-certificate \
  --domain-name regami.com \
  --subject-alternative-names "*.regami.com" "www.regami.com" \
  --validation-method DNS \
  --region us-east-1
```

**Covers:**
- regami.com
- www.regami.com
- *.regami.com (includes api.regami.com)

### Staging Certificate
```bash
aws acm request-certificate \
  --domain-name staging.regami.com \
  --subject-alternative-names "*.staging.regami.com" \
  --validation-method DNS \
  --region us-east-1
```

**Covers:**
- staging.regami.com
- *.staging.regami.com (includes api.staging.regami.com)

---

## Deployment Checklist

### Domain Setup
- [ ] Domain registered (regami.com)
- [ ] Route 53 hosted zone created
- [ ] Nameservers updated at registrar
- [ ] SSL certificate requested (production)
- [ ] SSL certificate validated (DNS records added)
- [ ] SSL certificate requested (staging)
- [ ] SSL certificate validated (staging)

### Backend Configuration
- [ ] `CORS_ORIGINS` set correctly per environment
- [ ] `APP_ENV` set (dev/staging/prod)
- [ ] `SECRET_KEY` generated uniquely per environment
- [ ] `DATABASE_URL` configured per environment
- [ ] `S3_BUCKET` named correctly per environment
- [ ] Sentry DSN configured (if using)

### Frontend Configuration
- [ ] `VITE_API_BASE_URL` set per environment
- [ ] Build process configured per environment
- [ ] CDN cache invalidation configured

### DNS Configuration
- [ ] Production frontend DNS (regami.com, www)
- [ ] Production API DNS (api.regami.com)
- [ ] Staging frontend DNS (staging.regami.com)
- [ ] Staging API DNS (api.staging.regami.com)
- [ ] DNS propagation verified (can take 5-15 minutes)

### Testing
- [ ] Local CORS working
- [ ] Staging CORS working
- [ ] Production CORS working
- [ ] API health checks passing
- [ ] Frontend loads correctly
- [ ] User registration works
- [ ] File uploads work (S3)
- [ ] Email sending works
- [ ] Push notifications work (if configured)

---

## Testing CORS

### Test Local CORS
```bash
curl -i -X OPTIONS http://localhost:8000/v1/auth/login \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST"

# Should return:
# Access-Control-Allow-Origin: http://localhost:5173
# Access-Control-Allow-Credentials: true
```

### Test Staging CORS
```bash
curl -i -X OPTIONS https://api.staging.regami.com/v1/auth/login \
  -H "Origin: https://staging.regami.com" \
  -H "Access-Control-Request-Method: POST"

# Should return:
# Access-Control-Allow-Origin: https://staging.regami.com
# Access-Control-Allow-Credentials: true
```

### Test Production CORS
```bash
curl -i -X OPTIONS https://api.regami.com/v1/auth/login \
  -H "Origin: https://regami.com" \
  -H "Access-Control-Request-Method: POST"

# Should return:
# Access-Control-Allow-Origin: https://regami.com
# Access-Control-Allow-Credentials: true
```

### Test CORS Rejection
```bash
# Test with unauthorized origin
curl -i -X OPTIONS https://api.regami.com/v1/auth/login \
  -H "Origin: https://evil.com" \
  -H "Access-Control-Request-Method: POST"

# Should NOT return Access-Control-Allow-Origin header
```

---

## Updating Domain Configuration

### Add New Domain

1. **Update Terraform:**
```hcl
# infra/terraform-serverless/main.tf
cors_configuration {
  allow_origins = [
    "https://regami.com",
    "https://www.regami.com",
    "https://newdomain.com"  # Add here
  ]
}
```

2. **Update Lambda Environment:**
```bash
aws lambda update-function-configuration \
  --function-name regami-api \
  --environment Variables="{...,CORS_ORIGINS=\"https://regami.com,https://www.regami.com,https://newdomain.com\"}"
```

3. **Update Frontend Build:**
```bash
# Add new deployment with appropriate API URL
VITE_API_BASE_URL=https://api.regami.com npm run build
```

### Remove Domain

1. Remove from Terraform CORS configuration
2. Remove from Lambda environment variables
3. Apply changes: `terraform apply`
4. Verify with CORS test (should be rejected)

---

## Troubleshooting

### CORS Error in Browser

**Symptom:** "Access to fetch at ... has been blocked by CORS policy"

**Checks:**
1. Verify origin is in allowed list
2. Check Lambda environment variables: `aws lambda get-function-configuration --function-name regami-api --query 'Environment.Variables.CORS_ORIGINS'`
3. Check API Gateway CORS configuration
4. Test with curl (see Testing CORS section)
5. Clear browser cache
6. Check for typos in domain names

### Wrong API URL

**Symptom:** Frontend can't reach API

**Checks:**
1. Check frontend build env: `VITE_API_BASE_URL`
2. Check browser console for API URL
3. Verify DNS records: `dig api.regami.com`
4. Test API directly: `curl https://api.regami.com/health`
5. Check CloudFront/CDN cache

### SSL Certificate Issues

**Symptom:** "Certificate not valid for domain"

**Checks:**
1. Verify certificate includes domain: `aws acm describe-certificate --certificate-arn ARN`
2. Check certificate is in us-east-1 region (CloudFront requirement - other resources in ca-central-1)
3. Verify DNS validation completed
4. Wait for certificate validation (can take 30 minutes)
5. Check CloudFront certificate association

---

## Related Documentation

- **[DEV.md](DEV.md)** - Local development setup
- **[STAGING.md](STAGING.md)** - Staging environment deployment
- **[SERVERLESS_DEPLOYMENT.md](SERVERLESS_DEPLOYMENT.md)** - Production deployment
- **[README.md](README.md)** - Project overview and quick start

---

## Support

- **Domain Issues:** Check Route 53 console and DNS propagation
- **CORS Issues:** Check browser console and backend logs
- **SSL Issues:** Check ACM certificate status
- **General:** See main documentation guides

---

**Last Updated:** November 30, 2025
**Domains:** regami.com, staging.regami.com
**Infrastructure:** AWS (Lambda, API Gateway, CloudFront, Route 53)
