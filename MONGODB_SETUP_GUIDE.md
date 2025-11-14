# MongoDB Atlas Setup Guide

## The Issue
Your MongoDB Atlas connection is failing because:
1. The connection string in your code was hardcoded and may be invalid
2. No proper `.env` file was configured with environment variables
3. The cluster or credentials may not be correct

## Solution Steps

### Step 1: Get Your MongoDB Atlas Connection String

1. **Go to MongoDB Atlas**: https://www.mongodb.com/cloud/atlas
2. **Login** to your account (create one if needed)
3. **Create a New Cluster** (if you don't have one):
   - Click "Build a Database"
   - Choose "Free Tier" (M0) for development
   - Select your region
   - Create cluster name
   - Click "Create"

4. **Get Connection String**:
   - Click "Connect" on your cluster
   - Choose "Connect your application"
   - Select "Python" and version "3.6 or later"
   - Copy the connection string - it will look like:
     ```
     mongodb+srv://username:password@cluster0.xxxxxx.mongodb.net/
     ```

5. **Create Database User**:
   - Go to "Database Access" in the left menu
   - Click "Add New Database User"
   - Choose "Password" authentication
   - Create username and password
   - Grant "Atlas admin" role

6. **Allow IP Access**:
   - Go to "Network Access" in the left menu
   - Click "Add IP Address"
   - Choose "Allow access from anywhere" (0.0.0.0/0) for development
   - Or add your specific IP address

### Step 2: Update Your .env File

Replace the `MONGODB_URI` in your `.env` file with your actual connection string:

```
MONGODB_URI=mongodb+srv://your_actual_username:your_actual_password@your_actual_cluster.mongodb.net/
```

Example:
```
MONGODB_URI=mongodb+srv://john_doe:my_password123@cluster0.abcde.mongodb.net/
```

### Step 3: Test the Connection

Run your application:
```bash
python app.py
```

You should see:
```
✅ MongoDB Atlas connected successfully
✅ Database initialized successfully
```

## Troubleshooting

### If You Still Get Connection Errors:

1. **Check Connection String**: Make sure there are no extra characters
2. **Verify Credentials**: Username and password must be exactly correct
3. **Check IP Access**: Your IP must be allowed in MongoDB Atlas
4. **Test Connection**: You can test with MongoDB Compass or MongoDB Shell

### Common Connection String Issues:

- **Don't include `<>` brackets** in your actual connection string
- **Special characters in password**: URL encode them (e.g., `@` becomes `%40`)
- **Wrong cluster name**: Make sure it matches your actual cluster
- **Case sensitivity**: Usernames and database names are case-sensitive

### Alternative: Use MongoDB Local Database

If you prefer not to use MongoDB Atlas, you can switch to a local MongoDB installation:
1. Install MongoDB locally
2. Update MONGODB_URI to: `mongodb://localhost:27017/`
3. Update DATABASE_NAME to your preferred name

## Security Notes

- Never commit your `.env` file to version control
- Use strong passwords for database users
- Consider using MongoDB's built-in authentication
- For production, restrict IP access to specific addresses