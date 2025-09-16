# 🚀 Deploy News Extractor to Web

## 📋 **Option 1: Render.com (Recommended - FREE)**

### Step 1: Prepare Code
1. Push code to GitHub repository
2. Make sure `render.yaml` and `requirements.txt` are included

### Step 2: Deploy on Render
1. Go to [render.com](https://render.com)
2. Sign up/Login với GitHub
3. Click **"New"** → **"Web Service"**
4. Connect GitHub repository
5. **Runtime**: Python 3
6. **Build Command**: `pip install -r requirements.txt`
7. **Start Command**: `gunicorn app:app`
8. Click **"Deploy"**

### Step 3: Environment Variables
Add these in Render dashboard:
```
GEMINI_API_KEY = AIzaSyBNU2IteZpqb93aISVU38Z0fN9r_Wc3_qs
PYTHON_VERSION = 3.11.0
DISPLAY = :99
CHROME_BIN = /usr/bin/google-chrome
CHROMEDRIVER_PATH = /usr/bin/chromedriver
```

⚠️ **CRITICAL**: Make sure `GEMINI_API_KEY` is set correctly - the app won't work without it!

---

## 🐳 **Option 2: Railway.app ($5/month)**

1. Go to [railway.app](https://railway.app)
2. **Deploy from GitHub**
3. Select repository
4. Add environment variables:
   ```
   GEMINI_API_KEY = AIzaSyBNU2IteZpqb93aISVU38Z0fN9r_Wc3_qs
   ```
5. Railway auto-detects Flask app

---

## ☁️ **Option 3: Heroku ($7/month)**

### Prerequisites
```bash
# Install Heroku CLI
# Windows: Download from heroku.com
# Mac: brew install heroku/brew/heroku
```

### Deploy Steps
```bash
# 1. Login
heroku login

# 2. Create app
heroku create your-news-extractor

# 3. Add buildpacks (for Chrome/Selenium)
heroku buildpacks:add --index 1 heroku/python
heroku buildpacks:add --index 2 https://github.com/heroku/heroku-buildpack-google-chrome
heroku buildpacks:add --index 3 https://github.com/heroku/heroku-buildpack-chromedriver

# 4. Set environment variables
heroku config:set GEMINI_API_KEY=AIzaSyBNU2IteZpqb93aISVU38Z0fN9r_Wc3_qs
heroku config:set GOOGLE_CHROME_BIN=/app/.apt/usr/bin/google-chrome
heroku config:set CHROMEDRIVER_PATH=/app/.chromedriver/bin/chromedriver

# 5. Deploy
git add .
git commit -m "Deploy to Heroku"
git push heroku main

# 6. Open app
heroku open
```

---

## 🔧 **Option 4: VPS (Digital Ocean, Vultr)**

### Server Setup
```bash
# 1. Create Ubuntu 22.04 VPS
# 2. SSH to server

# 3. Install dependencies
sudo apt update
sudo apt install python3 python3-pip nginx git
sudo apt install -y wget unzip
sudo apt install -y chromium-browser chromium-chromedriver

# 4. Clone repository
git clone your-repo-url
cd news-extractor

# 5. Install Python packages
pip3 install -r requirements.txt

# 6. Install PM2 for process management
sudo npm install -g pm2

# 7. Start app
pm2 start "gunicorn app:app --bind 0.0.0.0:5000" --name news-extractor

# 8. Setup Nginx (optional)
sudo nano /etc/nginx/sites-available/news-extractor
```

---

## 🔍 **Testing Deployment**

After deployment, test these URLs:
- `your-app-url.com/` - Main interface
- `your-app-url.com/extract` - Single extraction API
- `your-app-url.com/batch_extract` - Batch extraction API

---

## 🛠️ **Troubleshooting**

### Common Issues:

1. **Selenium not working**:
   ```
   # Add Chrome options for cloud deployment
   options.add_argument('--no-sandbox')
   options.add_argument('--disable-dev-shm-usage')
   ```

2. **Memory issues**:
   - Use smaller instance
   - Add swap file on VPS

3. **Slow startup**:
   - Chrome driver takes time to install
   - Normal on first deploy

---

## 💡 **Recommendations**

- **Free option**: Render.com
- **Best performance**: Railway.app 
- **Most flexible**: VPS
- **Enterprise**: Heroku

🎯 **Start with Render.com for testing, then upgrade if needed!**
