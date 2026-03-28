## ⚙️ Google Earth Engine (GEE) Setup

For the satellite simulation to work, the system needs to connect to the Google Earth Engine cloud. You must follow these steps before starting the server:

### 1. Prerequisites
You must have a Google account registered on [Google Earth Engine](https://earthengine.google.com/) and a Google Cloud Project with the Earth Engine API enabled.

### 2. Environment Variables
In the project root (at the same level as the `manage.py` file), create a file named exactly `.env`. Inside this file, enter your Google Cloud project ID as follows:

\`\`\`env
EE_PROJECT_ID=your-project-id-here
\`\`\`

### 3. Local Authentication
Before running the application for the first time, you must authorize your computer to access GEE resources. Open your terminal with the virtual environment activated and run:

\`\`\`bash
earthengine authenticate
\`\`\`

This will open a tab in your web browser. Sign in with your Google account, select your project, generate the access token, and paste it back into the terminal if prompted. 

Once authenticated, you can start the server with `python manage.py runserver`, and the machine learning model will work correctly