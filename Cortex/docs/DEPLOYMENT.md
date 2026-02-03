# Cortex Deployment Guide

## Production Deployment

### Prerequisites

- Node.js v20+
- All backend services running (InGress, InGest, OmegaKG, memOS)
- Environment variables configured

### Environment Variables

Create a `.env.production` file:

```env
# Backend Service URLs (update with production URLs)
VITE_API_OMEGA_URL=https://api.omegakg.yourdomain.com
VITE_API_INGEST_URL=https://api.ingest.yourdomain.com
VITE_API_MEMOS_URL=https://api.memos.yourdomain.com
VITE_API_INGRESS_URL=https://api.ingress.yourdomain.com

# API Security (required in production)
VITE_API_KEY=your-production-api-key

# Optional: Observability
VITE_LANGFUSE_PUBLIC_KEY=
VITE_LANGFUSE_SECRET_KEY=
```

### Build Process

```bash
# Install dependencies
npm ci

# Run tests
npm run test

# Build for production
npm run build

# Verify build
npm run preview
```

### Deployment Options

#### Option 1: Static Hosting (Recommended)

Build outputs static files to `dist/` folder.

**Vercel:**
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

**Netlify:**
```bash
# Install Netlify CLI
npm i -g netlify-cli

# Deploy
netlify deploy --prod --dir=dist
```

**GitHub Pages:**
```bash
# Install gh-pages
npm i -g gh-pages

# Deploy
gh-pages -d dist
```

#### Option 2: Docker

```dockerfile
# Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

```nginx
# nginx.conf
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Enable gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
}
```

Build and run:
```bash
docker build -t cortex-dashboard .
docker run -p 80:80 cortex-dashboard
```

#### Option 3: Self-Hosted Server

```bash
# Build
npm run build

# Serve with any static file server
npx serve -s dist -p 3000

# Or use Python
python -m http.server 3000 --directory dist
```

### Reverse Proxy Configuration

#### Nginx

```nginx
server {
    listen 443 ssl;
    server_name cortex.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:5173;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # SSE support for real-time features
    location /api/v1/telemetry/stream {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
    }
}
```

#### Caddy

```caddyfile
cortex.yourdomain.com {
    reverse_proxy localhost:5173
    
    # SSE support
    reverse_proxy /api/v1/telemetry/stream localhost:8000 {
        flush_interval -1
    }
}
```

### Health Checks

Add a health check endpoint to your deployment:

```bash
# Check if app is running
curl http://localhost:5173/health

# Should return: {"status":"ok"}
```

### Monitoring

#### Log Aggregation

Configure logging to send to your log aggregator:

```env
# .env.production
VITE_LOG_LEVEL=error
VITE_SENTRY_DSN=https://your-sentry-dsn
```

#### Uptime Monitoring

Use services like:
- UptimeRobot
- Pingdom
- StatusCake

Monitor these endpoints:
- `https://cortex.yourdomain.com` (Cortex UI)
- `https://api.ingress.yourdomain.com/health` (InGress)
- `https://api.ingest.yourdomain.com/health` (InGest)
- `https://api.omegakg.yourdomain.com/health` (OmegaKG)
- `https://api.memos.yourdomain.com/health` (memOS)

### Security Checklist

- [ ] API keys rotated and stored securely
- [ ] HTTPS enabled with valid SSL certificate
- [ ] CORS configured on backend services
- [ ] Rate limiting enabled on APIs
- [ ] Authentication implemented (if needed)
- [ ] Sensitive data not logged to console
- [ ] Build optimized for production (`npm run build`)

### Performance Optimization

1. **Enable Gzip/Brotli compression**
2. **Use CDN for static assets**
3. **Enable HTTP/2**
4. **Configure caching headers**
5. **Optimize images**

### Rollback Strategy

Keep previous builds for quick rollback:

```bash
# Tag builds with version
docker tag cortex-dashboard:latest cortex-dashboard:v1.2.3

# Rollback to previous version
docker stop cortex-dashboard
docker run -d --name cortex-dashboard cortex-dashboard:v1.2.2
```

### Troubleshooting

**Issue**: Blank page after deployment
- **Solution**: Check that `base` is set correctly in `vite.config.ts`

**Issue**: API calls failing
- **Solution**: Verify environment variables are set in production

**Issue**: SSE not working
- **Solution**: Ensure reverse proxy supports streaming (disable buffering)

**Issue**: Slow initial load
- **Solution**: Enable code splitting and lazy loading (already configured)

### Support

For deployment issues:
1. Check [Troubleshooting](#troubleshooting) section
2. Review [Developer Guide](./DEVELOPER_GUIDE.md)
3. Check [Soma Architecture](../docs/SYSTEM_ARCHITECTURE_SUMMARY.md)
