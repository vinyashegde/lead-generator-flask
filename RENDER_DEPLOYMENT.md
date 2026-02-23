# Deployment Guide: Lead Generator on Render

This guide outlines exactly how to deploy your Flask-based Lead Generation application to Render for free.

## Step 1: Deploying to Render
1. Go to [Render.com](https://render.com) and sign in.
2. Click **New +** and select **Web Service**.
3. Connect your GitHub account and select this newly created repository (`lead-generator-flask`).
4. Fill out the deployment details:
   - **Environment:** `Python 3`
   - **Branch:** `main`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
5. Click **Add Environment Variable** and add:
   - **Key:** `SERPAPI_KEY`
   - **Value:** *Your actual SerpAPI key*
6. Click **Create Web Service**. Wait 2-3 minutes for it to build and deploy.

---

## Step 2: Fixing the "Render Inactivity Timeout" Issue

**The Problem:** Render's free tier automatically spins down (sleeps) your application after 15 minutes of inactivity. When a user visits the app after it goes to sleep, they have to wait 30-50 seconds for it to wake back up.

**The Solution:** We can use a free service to "ping" the server every 14 minutes, tricking Render into thinking the server is constantly active.

I've built a lightweight `/ping` endpoint specifically for this (e.g., `https://your-app.onrender.com/ping`).

### Setup Instructions using UptimeRobot (Free & Reliable)
1. Go to [UptimeRobot.com](https://uptimerobot.com) and create a free account.
2. In the dashboard, click on **+ Add New Monitor**.
3. Configure the monitor exactly like this:
   - **Monitor Type:** HTTP(s)
   - **Friendly Name:** Keep Render Alive
   - **URL (or IP):** `https://YOUR-APP-NAME.onrender.com/ping` *(replace with your actual Render URL)*
   - **Monitoring Interval:** 14 minutes (10 minutes is also fine)
4. Click **Create Monitor** at the bottom (and click again to confirm).

**Result:** UptimeRobot will hit your `/ping` route automatically every 14 minutes. Render will see this traffic and will NEVER put your web application to sleep! Every user will get a fast loading experience.
