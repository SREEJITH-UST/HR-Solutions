# Security Configuration Guide

## 🔐 Environment Variables Setup

This project uses environment variables to securely manage sensitive information like API keys, database credentials, and email configurations.

### Quick Setup:

1. **Copy the example file:**
   ```bash
   cp env.example .env
   ```

2. **Edit `.env` with your actual values:**
   ```bash
   # Email Configuration
   EMAIL_HOST_USER=your_actual_gmail@gmail.com
   EMAIL_HOST_PASSWORD=your_actual_app_password
   
   # OpenAI Configuration
   OPENAI_API_KEY=sk-proj-your_actual_openai_api_key_here
   
   # Django Settings
   DEBUG=True
   SECRET_KEY=your_actual_django_secret_key
   ```

### 🚨 Security Best Practices:

1. **Never commit `.env` files to Git** - They're already in `.gitignore`
2. **Use strong, unique keys** - Generate Django secret keys with:
   ```python
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
3. **Rotate API keys regularly** - Especially for production environments
4. **Use environment-specific files** - `.env.development`, `.env.production`, etc.

### 🔑 Getting API Keys:

#### OpenAI API Key:
1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Sign up/Login to your account
3. Go to API Keys section
4. Create a new secret key
5. Copy the key (starts with `sk-proj-...`)

#### Gmail App Password:
1. Enable 2-Factor Authentication on Gmail
2. Go to Google Account Settings > Security
3. Generate an App Password for "Mail"
4. Use this password (not your regular Gmail password)

### 📁 File Security:

The following files are automatically ignored by Git:
- `.env` and `.env.*` (environment files)
- `*.key`, `*.pem`, `*.cert` (certificate files)
- `secrets.py`, `config.py` (configuration files)
- Any file containing: `secret`, `key`, `token`, `password`

### 🏗️ Production Deployment:

For production, set environment variables in your hosting platform:
- **Heroku**: Use `heroku config:set OPENAI_API_KEY=your_key`
- **Vercel**: Add to Environment Variables in dashboard
- **AWS/Docker**: Use environment variable injection

### ⚠️ If You Accidentally Commit Secrets:

1. **Immediately rotate/regenerate** all exposed keys
2. **Remove from Git history:**
   ```bash
   git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch env.example' --prune-empty --tag-name-filter cat -- --all
   git push --force --verbose --dry-run
   ```
3. **Update `.gitignore` and recommit**

### 🔍 Environment File Examples:

#### Development (`.env.development`):
```bash
DEBUG=True
OPENAI_API_KEY=sk-proj-development_key
EMAIL_HOST_USER=dev@company.com
DATABASE_URL=sqlite:///dev.db
```

#### Production (`.env.production`):
```bash
DEBUG=False
OPENAI_API_KEY=sk-proj-production_key
EMAIL_HOST_USER=noreply@company.com
DATABASE_URL=postgresql://user:pass@db:5432/hr_prod
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

### 📞 Support:

If you need help with environment setup or encounter security issues:
1. Check this documentation
2. Review Django's security best practices
3. Ensure all sensitive files are in `.gitignore`

---
**Remember**: Security is everyone's responsibility! 🛡️
