# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.

# Frontend Troubleshooting Guide

## Common Issues and Solutions

### 1. Frontend Won't Start

**Symptoms:** `npm run dev` fails or shows errors

**Solutions:**
- Make sure you're in the `frontend` directory
- Run `npm install` to install dependencies
- Check Node.js version (should be 16+)
- Clear cache: `rm -rf node_modules package-lock.json && npm install`

### 2. Backend Connection Issues

**Symptoms:** API calls fail, CORS errors, or "Network Error"

**Solutions:**
- Ensure backend is running on `http://localhost:8000`
- Check backend logs for errors
- Verify CORS is configured in `backend/main.py`
- If using WSL, you may need to use `http://localhost:8000` from Windows or the WSL IP address

### 3. File Upload Not Working

**Symptoms:** Upload button does nothing or shows errors

**Solutions:**
- Check browser console for errors
- Verify file format is supported (.txt, .docx, .pdf)
- Ensure backend `/api/upload` endpoint is working
- Check file size limits

### 4. Port Already in Use

**Symptoms:** "Port 5173 is already in use"

**Solutions:**
- Kill the process using the port
- Or change the port in `vite.config.js`:
  ```js
  export default defineConfig({
    plugins: [react()],
    server: {
      port: 5174
    }
  })
  ```

### 5. Module Not Found Errors

**Symptoms:** "Cannot find module" errors

**Solutions:**
- Run `npm install` again
- Delete `node_modules` and `package-lock.json`, then reinstall
- Check if all dependencies are in `package.json`

## Quick Start Checklist

1. ✅ Backend is running: `python backend/main.py` (port 8000)
2. ✅ Frontend dependencies installed: `cd frontend && npm install`
3. ✅ Frontend started: `npm run dev` (port 5173)
4. ✅ Browser opens to `http://localhost:5173`
5. ✅ No console errors in browser DevTools

## Testing the Connection

Open browser console and run:
```javascript
fetch('http://localhost:8000/api/health')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)
```

Should return: `{status: "ok", message: "Backend is running"}`

